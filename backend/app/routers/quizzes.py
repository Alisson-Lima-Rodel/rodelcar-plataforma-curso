"""Quiz por módulo — visão e resposta do ALUNO.

O gabarito (Alternativa.correta) NUNCA sai para o aluno: o GET devolve só o texto
das alternativas e a correção é feita no servidor no POST da tentativa.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.ratelimit import limiter
from app.core.vigencia import checar_vigencia_aluno
from app.dependencies import get_current_aluno
from app.models import (
    Alternativa,
    Aluno,
    Matricula,
    Modulo,
    Questao,
    Quiz,
    StatusMatricula,
    TentativaQuiz,
)
from app.schemas.quizzes import (
    AlternativaPublica,
    QuestaoPublica,
    QuizPublico,
    TentativaInput,
    TentativaResultado,
)

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


async def _quiz_e_matricula(
    quiz_id: uuid.UUID, aluno: Aluno, db: AsyncSession
) -> tuple[Quiz, uuid.UUID]:
    """Carrega o quiz (com questões/alternativas) e exige matrícula ATIVA do aluno
    no curso do quiz. Retorna (quiz, matricula_id)."""
    quiz = (
        await db.execute(
            select(Quiz)
            .where(Quiz.id == quiz_id, Quiz.ativo.is_(True))
            .options(selectinload(Quiz.questoes).selectinload(Questao.alternativas))
        )
    ).scalar_one_or_none()
    if quiz is None:
        raise _err(404, "QUIZ_NAO_ENCONTRADO", "Quiz não encontrado.")
    # Reconcilia vigência antes do gate de status (igual a aulas/progresso): uma
    # matrícula vencida mas ainda status=ativo não deve responder/aprovar quiz.
    await checar_vigencia_aluno(aluno.id, db)
    curso_id = await db.scalar(select(Modulo.curso_id).where(Modulo.id == quiz.modulo_id))
    mat = (
        await db.execute(
            select(Matricula.id).where(
                Matricula.aluno_id == aluno.id,
                Matricula.curso_id == curso_id,
                Matricula.status == StatusMatricula.ativo,
            )
        )
    ).scalar_one_or_none()
    if mat is None:
        raise _err(403, "SEM_ACESSO", "Você precisa ter o curso ativo para fazer o quiz.")
    return quiz, mat


async def _melhor_resultado(
    db: AsyncSession, matricula_id: uuid.UUID, quiz_id: uuid.UUID
) -> tuple[bool, float | None]:
    row = (
        await db.execute(
            select(
                func.bool_or(TentativaQuiz.aprovado),
                func.max(TentativaQuiz.nota),
            ).where(
                TentativaQuiz.matricula_id == matricula_id,
                TentativaQuiz.quiz_id == quiz_id,
            )
        )
    ).one()
    aprovado, melhor = row
    return bool(aprovado), (float(melhor) if melhor is not None else None)


@router.get("/{quiz_id}", response_model=QuizPublico)
async def obter_quiz(
    quiz_id: uuid.UUID,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    quiz, matricula_id = await _quiz_e_matricula(quiz_id, aluno, db)
    aprovado, melhor = await _melhor_resultado(db, matricula_id, quiz.id)
    return QuizPublico(
        id=quiz.id,
        titulo=quiz.titulo,
        nota_corte=float(quiz.nota_corte),
        aprovado=aprovado,
        melhor_nota=melhor,
        questoes=[
            QuestaoPublica(
                id=q.id,
                enunciado=q.enunciado,
                alternativas=[
                    AlternativaPublica(id=a.id, texto=a.texto) for a in q.alternativas
                ],
            )
            for q in quiz.questoes
        ],
    )


@router.post("/{quiz_id}/tentativas", response_model=TentativaResultado)
@limiter.limit("20/minute")
async def responder_quiz(
    request: Request,
    quiz_id: uuid.UUID,
    body: TentativaInput,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    quiz, matricula_id = await _quiz_e_matricula(quiz_id, aluno, db)
    if not quiz.questoes:
        raise _err(409, "QUIZ_SEM_QUESTOES", "Este quiz ainda não tem questões.")

    # Gabarito: para cada questão, o id da alternativa correta.
    correta_de = {
        q.id: next((a.id for a in q.alternativas if a.correta), None)
        for q in quiz.questoes
    }
    # Alternativas válidas por questão (só do PRÓPRIO quiz).
    alts_de = {q.id: {a.id for a in q.alternativas} for q in quiz.questoes}
    # Resposta do aluno: {questao_id: alternativa_id} (última vence se repetir).
    # Filtra pares que não pertencem a este quiz — não muda a nota (calculada
    # contra `correta_de`) e impede gravar UUIDs arbitrários no JSONB.
    escolha = {
        r.questao_id: r.alternativa_id
        for r in body.respostas
        if r.alternativa_id in alts_de.get(r.questao_id, ())
    }

    total = len(quiz.questoes)
    corretas = sum(
        1 for qid, certa in correta_de.items() if certa is not None and escolha.get(qid) == certa
    )
    nota = round(corretas / total * 100, 2) if total else 0.0
    aprovado = nota >= float(quiz.nota_corte)

    db.add(TentativaQuiz(
        matricula_id=matricula_id,
        quiz_id=quiz.id,
        nota=nota,
        aprovado=aprovado,
        respostas={str(k): str(v) for k, v in escolha.items()},
    ))
    await db.commit()
    return TentativaResultado(
        nota=nota, aprovado=aprovado, corretas=corretas, total=total
    )
