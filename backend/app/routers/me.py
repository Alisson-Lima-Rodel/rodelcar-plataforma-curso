import uuid
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.db import get_db
from app.core.stripe_admin import stripe_ativo
from app.core.stripe_refunds import (
    GARANTIA_DIAS,
    contar_estornos,
    executar_cancelamento,
    limite_cancelamento,
    motivo_bloqueio_autoatendimento,
    progresso_para_gate,
)
from app.core.vigencia import checar_vigencia_aluno
from app.dependencies import get_current_aluno
from app.core.referral import codigo_unico_indicacao
from app.models import (
    Aluno,
    Aula,
    Certificado,
    Cupom,
    Curso,
    Indicacao,
    Matricula,
    Modulo,
    Pagamento,
    Progresso,
    Quiz,
    StatusCurso,
    StatusMatricula,
    TentativaQuiz,
)
from app.schemas.me import (
    Alerta,
    CancelamentoResultado,
    CertificadoResumo,
    CupomResumo,
    CursoResumo,
    DashboardResponse,
    IndicacaoResponse,
    MatriculaGratuitaResponse,
    MatriculaItem,
    MatriculaListResponse,
    PlayerAula,
    PlayerCursoResponse,
    PlayerModulo,
    PlayerQuizResumo,
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

    # % por matrícula + maior progresso por assinatura (cancelar 1 revoga todas) e
    # nº de estornos da conta — entradas do gate anti-abuso do autoatendimento.
    pct_por_mat = {
        m.id: (
            round(sum(float(p.percentual) for p in m.progresso) / aula_counts[m.curso_id], 2)
            if aula_counts.get(m.curso_id)
            else 0.0
        )
        for m in matriculas
    }
    sub_max: dict = {}
    for m in matriculas:
        if m.stripe_subscription_id:
            sub_max[m.stripe_subscription_id] = max(
                sub_max.get(m.stripe_subscription_id, 0.0), pct_por_mat[m.id]
            )
    n_estornos = await contar_estornos(db, aluno.id)

    items = []
    for mat in matriculas:
        exp = _exp_aware(mat.data_expiracao)
        dias = max(0, (exp - agora).days)
        pct = pct_por_mat[mat.id]

        pag = pagamentos.get(mat.pagamento_id) if mat.pagamento_id else None
        limite = limite_cancelamento(pag)
        dentro_prazo = limite is not None and agora <= limite
        if pag is None:
            origem = "manual"
        elif mat.stripe_subscription_id:
            origem = "assinatura"
        else:
            origem = "avulsa"

        progresso_gate = (
            sub_max[mat.stripe_subscription_id]
            if mat.stripe_subscription_id
            else pct
        )
        bloqueio = motivo_bloqueio_autoatendimento(progresso_gate, n_estornos)
        reembolsavel = mat.status == StatusMatricula.ativo and dentro_prazo
        cancelavel = reembolsavel and bloqueio is None

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
                # só informa o motivo quando seria cancelável pelo prazo mas o
                # anti-abuso barrou (aí a UI manda falar com o suporte).
                motivo_bloqueio=bloqueio if (reembolsavel and bloqueio) else None,
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
    # Serializa os cancelamentos do MESMO aluno (lock por transação, liberado no
    # commit/rollback): evita duplo reembolso por clique-duplo/abas e o bypass do
    # teto de estornos via duas matrículas canceladas em paralelo.
    await db.execute(
        text("SELECT pg_advisory_xact_lock(:k)"),
        {"k": int.from_bytes(aluno.id.bytes[:8], "big", signed=True)},
    )
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

    # Anti-abuso (só o AUTOATENDIMENTO; o suporte reembolsa via /admin/reembolsos).
    bloqueio = motivo_bloqueio_autoatendimento(
        await progresso_para_gate(db, mat),
        await contar_estornos(db, aluno.id),
    )
    if bloqueio == "RECURSO_CONSUMIDO":
        raise _err(
            409, "RECURSO_CONSUMIDO",
            "Você já avançou mais de 20% no conteúdo. Para cancelar, fale com o suporte.",
        )
    if bloqueio == "LIMITE_REEMBOLSOS":
        raise _err(
            409, "LIMITE_REEMBOLSOS",
            "Você atingiu o limite de cancelamentos automáticos. Novos pedidos passam pelo suporte.",
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


@router.post(
    "/matriculas/gratis/{slug}",
    response_model=MatriculaGratuitaResponse,
    status_code=201,
)
async def matricular_gratis(
    slug: str,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """Matrícula GRATUITA: aluno cadastrado entra num curso marcado como `gratuito`
    sem Stripe. Ímã de leads. Idempotente: re-chamar reativa/renova a vigência."""
    # Só curso ATIVO é matriculável por slug (em_desenvolvimento/inativo não —
    # mesma regra do checkout, fecha a superfície de transação gratuita).
    curso = (
        await db.execute(
            select(Curso).where(
                Curso.slug == slug, Curso.status == StatusCurso.ativo
            )
        )
    ).scalar_one_or_none()
    if curso is None:
        raise _err(404, "CURSO_NAO_ENCONTRADO", "Curso não encontrado.")
    if not curso.gratuito:
        raise _err(403, "CURSO_NAO_GRATUITO", "Este curso não é gratuito.")

    nova_exp = datetime.now(timezone.utc) + timedelta(days=curso.validade_dias)

    async def _carrega() -> Matricula | None:
        return (
            await db.execute(
                select(Matricula).where(
                    Matricula.aluno_id == aluno.id, Matricula.curso_id == curso.id
                )
            )
        ).scalar_one_or_none()

    def _renovar_se_preciso(m: Matricula) -> None:
        # Já vigente → NÃO estende: senão o aluno renovaria infinitamente (reset da
        # expiração a cada chamada) e o curso gratuito nunca venceria.
        vigente = (
            m.status == StatusMatricula.ativo
            and _exp_aware(m.data_expiracao) > datetime.now(timezone.utc)
        )
        if not vigente:
            m.status = StatusMatricula.ativo
            m.data_expiracao = nova_exp

    mat = await _carrega()
    ja = mat is not None
    if mat is None:
        mat = Matricula(
            aluno_id=aluno.id,
            curso_id=curso.id,
            status=StatusMatricula.ativo,
            data_expiracao=nova_exp,
        )
        db.add(mat)
        try:
            await db.commit()
        except IntegrityError:
            # Corrida: dois cliques simultâneos. O unique (aluno,curso) garante 1;
            # cai no caminho de reativação em vez de 500.
            await db.rollback()
            mat = await _carrega()
            ja = True
            if mat is None:  # pragma: no cover (defensivo)
                raise _err(409, "MATRICULA_CONFLITO", "Tente novamente.")
            _renovar_se_preciso(mat)
            await db.commit()
    else:
        _renovar_se_preciso(mat)
        await db.commit()
    await db.refresh(mat)
    return MatriculaGratuitaResponse(
        matricula_id=mat.id, slug=curso.slug, status=mat.status.value, ja_matriculado=ja
    )


@router.get("/indicacoes", response_model=IndicacaoResponse)
async def minhas_indicacoes(
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """Indique-e-ganhe: código pessoal, total de indicados e cupons ganhos.
    Gera o código na hora para contas antigas (criadas antes do recurso)."""
    if not aluno.codigo_indicacao:
        aluno.codigo_indicacao = await codigo_unico_indicacao(db)
        try:
            await db.commit()
        except IntegrityError:
            # Dois GETs simultâneos geraram códigos diferentes p/ o mesmo aluno; o
            # unique barra o 2º. Recarrega o que ficou (sem 500 num GET).
            await db.rollback()
            await db.refresh(aluno)

    total = await db.scalar(
        select(func.count(Indicacao.id)).where(Indicacao.indicador_id == aluno.id)
    )
    agora = datetime.now(timezone.utc)
    # Conta só recompensas cujo cupom do indicador AINDA está ativo e válido —
    # bate com a lista de cupons exibida (não infla com recompensas cujo cupom já
    # expirou ou foi desativado pelo admin).
    recompensados = await db.scalar(
        select(func.count(Indicacao.id))
        .join(Cupom, Indicacao.cupom_indicador_id == Cupom.id)
        .where(
            Indicacao.indicador_id == aluno.id,
            Indicacao.status == "recompensado",
            Cupom.ativo.is_(True),
            or_(Cupom.validade.is_(None), Cupom.validade > agora),
        )
    )
    cupons = (
        await db.execute(
            select(Cupom)
            .where(Cupom.aluno_id == aluno.id, Cupom.ativo.is_(True))
            .order_by(Cupom.criado_em.desc())
        )
    ).scalars().all()
    cupons_validos = [
        CupomResumo(
            codigo=c.codigo, tipo=c.tipo, valor=float(c.valor), validade=c.validade
        )
        for c in cupons
        if c.validade is None or _exp_aware(c.validade) > agora
    ]
    return IndicacaoResponse(
        codigo=aluno.codigo_indicacao,
        total_indicados=total or 0,
        total_recompensados=recompensados or 0,
        cupons=cupons_validos,
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
            # Só matrícula ATIVA: não oferecer "retomar" um curso estornado/
            # expirado (abriria o player e bateria no 403 da aula).
            .where(
                Matricula.aluno_id == aluno.id,
                Matricula.status == StatusMatricula.ativo,
            )
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

    # Quizzes ATIVOS do curso (por módulo) + quais a matrícula já passou.
    quiz_rows = (
        await db.execute(
            select(Quiz)
            .join(Modulo, Quiz.modulo_id == Modulo.id)
            .where(Modulo.curso_id == curso.id, Quiz.ativo.is_(True))
        )
    ).scalars().all()
    quiz_por_modulo = {q.modulo_id: q for q in quiz_rows}
    aprovados: set = set()
    if quiz_rows:
        aprovados = set(
            (
                await db.execute(
                    select(TentativaQuiz.quiz_id)
                    .where(
                        TentativaQuiz.matricula_id == matricula.id,
                        TentativaQuiz.quiz_id.in_([q.id for q in quiz_rows]),
                        TentativaQuiz.aprovado.is_(True),
                    )
                    .distinct()
                )
            ).scalars().all()
        )

    ratio = settings.CERT_MIN_WATCH_RATIO
    modulos: list[PlayerModulo] = []
    total = 0
    concluidas = 0
    cert_aulas_ok = 0          # aulas que satisfazem o gate do certificado
    tem_aula_sem_duracao = False
    soma_pct = 0.0
    for m in sorted(curso.modulos, key=lambda x: x.ordem):
        aulas = []
        for a in sorted(m.aulas, key=lambda x: x.ordem):
            p = pmap.get(a.id)
            feita = bool(p.concluida) if p else False   # checkmark do usuário (UI)
            pct = float(p.percentual) if p else 0.0
            total += 1
            concluidas += 1 if feita else 0
            soma_pct += pct
            # Cert-elegível = mesmo critério do emitir_certificado: concluída +
            # tempo REAL assistido >= ratio*duração + duração cadastrada (>0).
            dur = a.duracao_segundos or 0
            if dur <= 0:
                tem_aula_sem_duracao = True
            elif p and p.concluida and p.segundos_assistidos >= dur * ratio:
                cert_aulas_ok += 1
            aulas.append(
                PlayerAula(
                    id=a.id,
                    titulo=a.titulo,
                    duracao_label=_dur_label(a.duracao_segundos),
                    concluida=feita,
                    percentual=pct,
                )
            )
        quiz_m = quiz_por_modulo.get(m.id)
        modulos.append(
            PlayerModulo(
                id=m.id, titulo=m.titulo, ordem=m.ordem, aulas=aulas,
                quiz=(
                    PlayerQuizResumo(
                        id=quiz_m.id, titulo=quiz_m.titulo,
                        aprovado=quiz_m.id in aprovados,
                    )
                    if quiz_m is not None else None
                ),
            )
        )

    pct_curso = round(soma_pct / total, 1) if total else 0.0
    # Concluído = exatamente o gate do emitir_certificado: matrícula ATIVA + todas
    # as aulas cert-elegíveis (concluída + tempo assistido + duração>0) + todos os
    # quizzes ativos aprovados. Casar com o gate evita prometer na UI um certificado
    # que o POST recusaria (409 CURSO_NAO_CONCLUIDO / QUIZ_PENDENTE / DURACAO_*).
    quizzes_ok = all(q.id in aprovados for q in quiz_rows)
    concluido = (
        matricula.status == StatusMatricula.ativo
        and total > 0
        and not tem_aula_sem_duracao
        and cert_aulas_ok == total
        and quizzes_ok
    )

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
