from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.vigencia import checar_vigencia_aluno
from app.dependencies import get_current_aluno
from app.models import (
    Aluno,
    Aula,
    Certificado,
    Curso,
    Matricula,
    Modulo,
    Progresso,
    StatusMatricula,
)
from app.schemas.me import (
    Alerta,
    CursoResumo,
    DashboardResponse,
    MatriculaItem,
    MatriculaListResponse,
    ResumoDashboard,
    UltimaAula,
)

router = APIRouter(prefix="/me", tags=["me"])


def _exp_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/matriculas", response_model=MatriculaListResponse)
async def listar_matriculas(
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    await checar_vigencia_aluno(aluno.id, db)
    agora = datetime.now(timezone.utc)

    stmt = (
        select(Matricula)
        .where(Matricula.aluno_id == aluno.id)
        .options(selectinload(Matricula.curso), selectinload(Matricula.progresso))
        .order_by(Matricula.data_inicio.desc())
    )
    matriculas = (await db.execute(stmt)).scalars().all()

    # Contagem de aulas por curso (para progresso_percentual correto)
    curso_ids = list({m.curso_id for m in matriculas})
    aula_counts: dict = {}
    if curso_ids:
        rows = (
            await db.execute(
                select(Modulo.curso_id, func.count(Aula.id).label("n"))
                .join(Aula, Aula.modulo_id == Modulo.id)
                .where(Modulo.curso_id.in_(curso_ids))
                .group_by(Modulo.curso_id)
            )
        ).all()
        aula_counts = {row.curso_id: row.n for row in rows}

    items = []
    for mat in matriculas:
        exp = _exp_aware(mat.data_expiracao)
        dias = max(0, (exp - agora).days)
        total = aula_counts.get(mat.curso_id, 0)
        soma_pct = sum(float(p.percentual) for p in mat.progresso)
        pct = round(soma_pct / total, 2) if total > 0 else 0.0
        items.append(
            MatriculaItem(
                id=mat.id,
                curso=CursoResumo(
                    id=mat.curso.id,
                    slug=mat.curso.slug,
                    titulo=mat.curso.titulo,
                ),
                status=mat.status,
                data_inicio=mat.data_inicio,
                data_expiracao=mat.data_expiracao,
                dias_restantes=dias,
                progresso_percentual=pct,
            )
        )

    return MatriculaListResponse(items=items)


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    await checar_vigencia_aluno(aluno.id, db)
    agora = datetime.now(timezone.utc)

    # Última aula acessada (maior atualizado_em no Progresso)
    row = (
        await db.execute(
            select(Progresso, Aula, Curso)
            .join(Aula, Progresso.aula_id == Aula.id)
            .join(Modulo, Aula.modulo_id == Modulo.id)
            .join(Curso, Modulo.curso_id == Curso.id)
            .join(Matricula, Progresso.matricula_id == Matricula.id)
            .where(Matricula.aluno_id == aluno.id)
            .order_by(Progresso.atualizado_em.desc())
            .limit(1)
        )
    ).first()
    ultima_aula = None
    if row:
        prog, aula, curso = row
        ultima_aula = UltimaAula(
            aula_id=aula.id,
            titulo=aula.titulo,
            curso_slug=curso.slug,
            percentual=float(prog.percentual),
        )

    # Alertas: matrículas ativas expirando em ≤ 15 dias
    alerta_threshold = agora + timedelta(days=15)
    alerta_rows = (
        await db.execute(
            select(Matricula, Curso.titulo)
            .join(Curso, Matricula.curso_id == Curso.id)
            .where(
                Matricula.aluno_id == aluno.id,
                Matricula.status == StatusMatricula.ativo,
                Matricula.data_expiracao <= alerta_threshold,
            )
        )
    ).all()
    alertas: list[Alerta] = []
    for mat, titulo_curso in alerta_rows:
        exp = _exp_aware(mat.data_expiracao)
        dias = max(0, (exp - agora).days)
        nivel = "danger" if dias <= 3 else "warning"
        sufixo = "s" if dias != 1 else ""
        alertas.append(
            Alerta(
                tipo="vigencia",
                nivel=nivel,
                mensagem=f"Plano '{titulo_curso}' expira em {dias} dia{sufixo}.",
            )
        )

    # Resumo
    cursos_ativos = await db.scalar(
        select(func.count(Matricula.id)).where(
            Matricula.aluno_id == aluno.id,
            Matricula.status == StatusMatricula.ativo,
        )
    ) or 0

    aulas_concluidas = await db.scalar(
        select(func.count(Progresso.id))
        .join(Matricula, Progresso.matricula_id == Matricula.id)
        .where(Matricula.aluno_id == aluno.id, Progresso.concluida.is_(True))
    ) or 0

    certificados = await db.scalar(
        select(func.count(Certificado.id))
        .join(Matricula, Certificado.matricula_id == Matricula.id)
        .where(Matricula.aluno_id == aluno.id)
    ) or 0

    return DashboardResponse(
        ultima_aula=ultima_aula,
        alertas=alertas,
        resumo=ResumoDashboard(
            cursos_ativos=cursos_ativos,
            aulas_concluidas=aulas_concluidas,
            certificados=certificados,
        ),
    )
