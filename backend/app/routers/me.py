import uuid
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.stripe_admin import stripe_ativo
from app.core.stripe_refunds import (
    GARANTIA_DIAS,
    executar_cancelamento,
    limite_cancelamento,
)
from app.core.vigencia import checar_vigencia_aluno
from app.dependencies import get_current_aluno
from app.models import (
    Aluno,
    Aula,
    Certificado,
    Curso,
    Matricula,
    Modulo,
    Pagamento,
    Progresso,
    StatusMatricula,
)
from app.schemas.me import (
    Alerta,
    CancelamentoResultado,
    CertificadoResumo,
    CursoResumo,
    DashboardResponse,
    MatriculaItem,
    MatriculaListResponse,
    PlayerAula,
    PlayerCursoResponse,
    PlayerModulo,
    ResumoDashboard,
    UltimaAula,
)

router = APIRouter(prefix="/me", tags=["me"])


def _exp_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _dur_label(segundos: int | None) -> str:
    m, s = divmod(int(segundos or 0), 60)
    return f"{m:02d}:{s:02d}"


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

    # Pagamentos vinculados (p/ janela de arrependimento de 7 dias)
    pag_ids = [m.pagamento_id for m in matriculas if m.pagamento_id]
    pagamentos: dict = {}
    if pag_ids:
        rows = (
            await db.execute(select(Pagamento).where(Pagamento.id.in_(pag_ids)))
        ).scalars().all()
        pagamentos = {p.id: p for p in rows}

    items = []
    for mat in matriculas:
        exp = _exp_aware(mat.data_expiracao)
        dias = max(0, (exp - agora).days)
        total = aula_counts.get(mat.curso_id, 0)
        soma_pct = sum(float(p.percentual) for p in mat.progresso)
        pct = round(soma_pct / total, 2) if total > 0 else 0.0

        pag = pagamentos.get(mat.pagamento_id) if mat.pagamento_id else None
        limite = limite_cancelamento(pag)
        cancelavel = (
            mat.status == StatusMatricula.ativo
            and limite is not None
            and agora <= limite
        )
        if pag is None:
            origem = "manual"
        elif mat.stripe_subscription_id:
            origem = "assinatura"
        else:
            origem = "avulsa"

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
                origem=origem,
                cancelavel=cancelavel,
                cancelavel_ate=limite if cancelavel else None,
            )
        )

    return MatriculaListResponse(items=items)


@router.post("/matriculas/{matricula_id}/cancelar", response_model=CancelamentoResultado)
async def cancelar_matricula(
    matricula_id: uuid.UUID,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """Direito de arrependimento (CDC art. 49): até 7 dias após a compra, cancela
    com reembolso INTEGRAL via Stripe. Compra avulsa → estorna e expira o curso;
    assinatura → estorna, cancela a assinatura e revoga o catálogo dela."""
    mat = (
        await db.execute(
            select(Matricula).where(
                Matricula.id == matricula_id, Matricula.aluno_id == aluno.id
            )
        )
    ).scalar_one_or_none()
    if mat is None:
        # 404 (não 403) para não revelar matrícula alheia existente.
        raise _err(404, "MATRICULA_NAO_ENCONTRADA", "Matrícula não encontrada.")
    if mat.status != StatusMatricula.ativo:
        raise _err(409, "MATRICULA_NAO_ATIVA", "Esta matrícula não está ativa.")

    pag = await db.get(Pagamento, mat.pagamento_id) if mat.pagamento_id else None
    limite = limite_cancelamento(pag)
    if limite is None:
        raise _err(
            409, "SEM_PAGAMENTO_REEMBOLSAVEL",
            "Não há pagamento online vinculado a esta matrícula para reembolsar.",
        )
    if datetime.now(timezone.utc) > limite:
        raise _err(
            400, "FORA_DO_PRAZO",
            f"O prazo de arrependimento ({GARANTIA_DIAS} dias) já passou.",
        )
    if not stripe_ativo():
        raise _err(503, "STRIPE_NAO_CONFIGURADO", "Reembolsos indisponíveis no momento.")

    # Stripe primeiro; banco só muda se o estorno/cancelamento der certo. A
    # revogação do catálogo é idempotente com o webhook subscription.deleted.
    try:
        assinatura_cancelada, cursos_revogados = await executar_cancelamento(db, mat, pag)
    except stripe.error.StripeError:
        raise _err(502, "STRIPE_ERRO", "Falha ao processar o reembolso — nada foi alterado.")

    await db.commit()
    return CancelamentoResultado(
        matricula_id=mat.id,
        reembolsado=True,
        assinatura_cancelada=assinatura_cancelada,
        cursos_revogados=cursos_revogados,
    )


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


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


@router.get("/cursos/{slug}", response_model=PlayerCursoResponse)
async def player_curso(
    slug: str,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """Estrutura do curso + progresso por aula do aluno (alimenta o player e o
    certificado). Exige matrícula no curso (qualquer status)."""
    await checar_vigencia_aluno(aluno.id, db)

    curso = (
        await db.execute(
            select(Curso)
            .where(Curso.slug == slug)
            .options(selectinload(Curso.modulos).selectinload(Modulo.aulas))
        )
    ).scalar_one_or_none()
    if curso is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {
                "code": "CURSO_NAO_ENCONTRADO",
                "message": "Curso não encontrado.",
                "details": None,
            }},
        )

    matricula = (
        await db.execute(
            select(Matricula).where(
                Matricula.aluno_id == aluno.id,
                Matricula.curso_id == curso.id,
            )
        )
    ).scalar_one_or_none()
    if matricula is None:
        raise HTTPException(
            status_code=403,
            detail={"error": {
                "code": "ACESSO_NEGADO",
                "message": "Você não possui matrícula neste curso.",
                "details": None,
            }},
        )

    progs = (
        await db.execute(
            select(Progresso).where(Progresso.matricula_id == matricula.id)
        )
    ).scalars().all()
    pmap = {p.aula_id: p for p in progs}

    modulos: list[PlayerModulo] = []
    total = 0
    concluidas = 0
    soma_pct = 0.0
    for m in sorted(curso.modulos, key=lambda x: x.ordem):
        aulas = []
        for a in sorted(m.aulas, key=lambda x: x.ordem):
            p = pmap.get(a.id)
            feita = bool(p.concluida) if p else False
            pct = float(p.percentual) if p else 0.0
            total += 1
            concluidas += 1 if feita else 0
            soma_pct += pct
            aulas.append(
                PlayerAula(
                    id=a.id,
                    titulo=a.titulo,
                    duracao_label=_dur_label(a.duracao_segundos),
                    concluida=feita,
                    percentual=pct,
                )
            )
        modulos.append(
            PlayerModulo(id=m.id, titulo=m.titulo, ordem=m.ordem, aulas=aulas)
        )

    pct_curso = round(soma_pct / total, 1) if total else 0.0
    concluido = total > 0 and concluidas == total

    cert = (
        await db.execute(
            select(Certificado).where(Certificado.matricula_id == matricula.id)
        )
    ).scalar_one_or_none()

    return PlayerCursoResponse(
        matricula_id=matricula.id,
        curso=CursoResumo(id=curso.id, slug=curso.slug, titulo=curso.titulo),
        horas=curso.horas,
        status=matricula.status,
        progresso_percentual=pct_curso,
        concluido=concluido,
        certificado=(
            CertificadoResumo(codigo=cert.codigo_verificacao, emitido_em=cert.emitido_em)
            if cert
            else None
        ),
        modulos=modulos,
    )
