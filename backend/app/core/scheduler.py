"""APScheduler + job diário de vigência e notificações."""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.orm import selectinload

from app.core.db import AsyncSessionLocal
from app.core.notificacoes import MensagemNotificacao, enviar_email, enviar_whatsapp
from app.models import (
    CanalNotificacao,
    Lead,
    Matricula,
    Notificacao,
    RefreshToken,
    StatusLead,
    StatusMatricula,
    StatusNotificacao,
    TipoNotificacao,
)

logger = logging.getLogger(__name__)

# Tokens revogados ficam por este período (auditoria / detecção de reuso) antes
# de serem apagados; expirados saem assim que vencem.
REFRESH_RETENCAO_REVOGADOS_DIAS = 30

# Leads de captação finalizados (concluido/perdido) são expurgados após este
# período — minimização/descarte após a finalidade (LGPD).
LEAD_RETENCAO_DIAS = 180

# (marco, dias_antes_da_expiracao, tipo_notificacao)
_MARCOS_PREVIA = [
    ("15d", 15, TipoNotificacao.vigencia_proxima),
    ("7d",  7,  TipoNotificacao.vigencia_proxima),
    ("1d",  1,  TipoNotificacao.vigencia_proxima),
]


# ── Lógica central (reutilizada pelo job e pelo endpoint HTTP) ─────────────────

async def executar_ciclo_vigencia(dry_run: bool = False) -> dict:
    """Varre matrículas, marca expiradas, enfileira e envia notificações.

    Idempotente: a chave única (matricula_id, tipo, canal, marco) garante que
    o mesmo marco nunca é reenviado ao mesmo aluno.
    """
    now = datetime.now(timezone.utc)
    verificadas = enfileiradas = enviadas = falhas = 0

    async with AsyncSessionLocal() as db:
        # 1. Marca ativas vencidas como expirado e coleta os IDs
        stmt = (
            update(Matricula)
            .where(
                Matricula.status == StatusMatricula.ativo,
                Matricula.data_expiracao < now,
            )
            .values(status=StatusMatricula.expirado)
            .returning(Matricula.id)
        )
        result = await db.execute(stmt)
        expiradas_ids = list(result.scalars().all())

        if not dry_run and expiradas_ids:
            await db.commit()

        # 2. Notifica as recém-expiradas
        if expiradas_ids:
            rows = await db.execute(
                select(Matricula)
                .where(Matricula.id.in_(expiradas_ids))
                .options(selectinload(Matricula.aluno), selectinload(Matricula.curso))
            )
            for m in rows.scalars().all():
                verificadas += 1
                for canal in (CanalNotificacao.email, CanalNotificacao.whatsapp):
                    nova, ok = await _processar_notificacao(
                        db, m, TipoNotificacao.vigencia_expirada, canal, "expirado", now, dry_run
                    )
                    if nova:
                        enfileiradas += 1
                    if ok:
                        enviadas += 1
                    elif nova:
                        falhas += 1

        # 3. Marcos de pré-aviso (15d / 7d / 1d)
        for marco, dias, tipo in _MARCOS_PREVIA:
            # Janela de ±12 h para tolerar horário do job
            alvo_inicio = now + timedelta(days=dias) - timedelta(hours=12)
            alvo_fim    = now + timedelta(days=dias) + timedelta(hours=12)

            rows = await db.execute(
                select(Matricula)
                .where(
                    Matricula.status == StatusMatricula.ativo,
                    Matricula.data_expiracao >= alvo_inicio,
                    Matricula.data_expiracao <= alvo_fim,
                )
                .options(selectinload(Matricula.aluno), selectinload(Matricula.curso))
            )
            for m in rows.scalars().all():
                verificadas += 1
                for canal in (CanalNotificacao.email, CanalNotificacao.whatsapp):
                    nova, ok = await _processar_notificacao(
                        db, m, tipo, canal, marco, now, dry_run
                    )
                    if nova:
                        enfileiradas += 1
                    if ok:
                        enviadas += 1
                    elif nova:
                        falhas += 1

    logger.info(
        "Ciclo de vigência concluído: verificadas=%d enfileiradas=%d "
        "enviadas=%d falhas=%d dry_run=%s",
        verificadas, enfileiradas, enviadas, falhas, dry_run,
    )
    return {
        "verificadas": verificadas,
        "enfileiradas": enfileiradas,
        "enviadas": enviadas,
        "falhas": falhas,
    }


async def _processar_notificacao(
    db,
    matricula: Matricula,
    tipo: TipoNotificacao,
    canal: CanalNotificacao,
    marco: str,
    now: datetime,
    dry_run: bool,
) -> tuple[bool, bool]:
    """Retorna (nova, enviada_com_sucesso).

    nova=True  → notificação não existia antes desta execução.
    nova=False → já havia registro (idempotência), nada foi feito.
    """
    # Idempotência: chave única (matricula_id, tipo, canal, marco)
    existing = await db.execute(
        select(Notificacao).where(
            Notificacao.matricula_id == matricula.id,
            Notificacao.tipo == tipo,
            Notificacao.canal == canal,
            Notificacao.marco == marco,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False, False

    if dry_run:
        return True, False  # contabiliza sem persistir/enviar

    # Cria registro pendente antes de tentar o envio
    notif = Notificacao(
        aluno_id=matricula.aluno_id,
        matricula_id=matricula.id,
        canal=canal,
        tipo=tipo,
        marco=marco,
        status=StatusNotificacao.pendente,
        payload={},
    )
    db.add(notif)
    await db.flush()  # obtém o id gerado

    msg = MensagemNotificacao(
        aluno_id=matricula.aluno_id,
        aluno_nome=matricula.aluno.nome,
        aluno_email=matricula.aluno.email,
        aluno_telefone=matricula.aluno.telefone,
        tipo=tipo,
        marco=marco,
        curso_titulo=matricula.curso.titulo,
        data_expiracao=matricula.data_expiracao,
    )

    provedor_msg_id: str | None
    if canal == CanalNotificacao.email:
        provedor_msg_id = await enviar_email(msg)
    else:
        provedor_msg_id = await enviar_whatsapp(msg)

    ok = provedor_msg_id is not None
    notif.status = StatusNotificacao.enviada if ok else StatusNotificacao.falhou
    if ok:
        notif.enviada_em = now
        notif.provedor_msg_id = provedor_msg_id

    await db.commit()
    return True, ok


# ── Limpeza de refresh tokens ─────────────────────────────────────────────────

async def limpar_refresh_tokens(db) -> int:
    """Apaga refresh tokens vencidos e revogados antigos. Retorna nº removidos.

    Mantém revogados recentes (< REFRESH_RETENCAO_REVOGADOS_DIAS) p/ a detecção
    de reuso continuar funcionando dentro da janela de validade.
    """
    now = datetime.now(timezone.utc)
    corte_revogados = now - timedelta(days=REFRESH_RETENCAO_REVOGADOS_DIAS)
    result = await db.execute(
        delete(RefreshToken).where(
            or_(
                RefreshToken.expira_em < now,
                and_(
                    RefreshToken.revogado.is_(True),
                    RefreshToken.revogado_em < corte_revogados,
                ),
            )
        )
    )
    await db.commit()
    return result.rowcount or 0


# ── Expurgo de leads finalizados (LGPD) ───────────────────────────────────────

async def limpar_leads_antigos(db) -> int:
    """Apaga leads finalizados (concluido/perdido) com mais de LEAD_RETENCAO_DIAS.

    Dados de captação contêm PII (nome/telefone/e-mail/mensagem); após a finalidade
    do follow-up comercial, são descartados (minimização — LGPD).
    """
    corte = datetime.now(timezone.utc) - timedelta(days=LEAD_RETENCAO_DIAS)
    result = await db.execute(
        delete(Lead).where(
            Lead.status.in_((StatusLead.concluido, StatusLead.perdido)),
            Lead.criado_em < corte,
        )
    )
    await db.commit()
    return result.rowcount or 0


# ── Scheduler ─────────────────────────────────────────────────────────────────

scheduler = AsyncIOScheduler()


async def _job_vigencia_diaria() -> None:
    try:
        await executar_ciclo_vigencia()
    except Exception:
        logger.exception("Erro não tratado no job de vigência diária")


async def _job_limpeza_tokens() -> None:
    try:
        async with AsyncSessionLocal() as db:
            removidos = await limpar_refresh_tokens(db)
        logger.info("Limpeza de refresh tokens concluída — %d removidos", removidos)
    except Exception:
        logger.exception("Erro não tratado no job de limpeza de refresh tokens")


async def _job_limpeza_leads() -> None:
    try:
        async with AsyncSessionLocal() as db:
            removidos = await limpar_leads_antigos(db)
        logger.info("Expurgo de leads finalizados concluído — %d removidos", removidos)
    except Exception:
        logger.exception("Erro não tratado no job de expurgo de leads")


async def _job_google_reviews() -> None:
    try:
        from app.core.google_reviews import atualizar_cache, google_ativo

        if not google_ativo():
            return
        async with AsyncSessionLocal() as db:
            await atualizar_cache(db)
    except Exception:
        logger.exception("Erro não tratado no job de avaliações do Google")


async def _job_recompensar_indicacoes() -> None:
    """Retoma recompensas de indicação que ficaram presas (ex.: Stripe fora no
    webhook). De hora em hora p/ o aluno não esperar demais pelo cupom."""
    try:
        from app.core.referral import processar_recompensas_pendentes

        async with AsyncSessionLocal() as db:
            feitas = await processar_recompensas_pendentes(db)
        if feitas:
            logger.info("Recompensas de indicação retomadas: %d", feitas)
    except Exception:
        logger.exception("Erro não tratado no job de recompensas de indicação")


def iniciar_scheduler() -> None:
    scheduler.add_job(
        _job_vigencia_diaria,
        CronTrigger(hour=6, minute=0, timezone="UTC"),
        id="vigencia_diaria",
        replace_existing=True,
    )
    scheduler.add_job(
        _job_limpeza_tokens,
        CronTrigger(hour=6, minute=10, timezone="UTC"),
        id="limpeza_refresh_tokens",
        replace_existing=True,
    )
    scheduler.add_job(
        _job_limpeza_leads,
        CronTrigger(hour=6, minute=20, timezone="UTC"),
        id="limpeza_leads",
        replace_existing=True,
    )
    scheduler.add_job(
        _job_google_reviews,
        CronTrigger(hour=6, minute=30, timezone="UTC"),
        id="google_reviews",
        replace_existing=True,
    )
    scheduler.add_job(
        _job_recompensar_indicacoes,
        CronTrigger(minute=45, timezone="UTC"),  # de hora em hora
        id="recompensar_indicacoes",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler iniciado — vigência 06:00, limpeza de tokens 06:10, "
        "expurgo de leads 06:20, avaliações Google 06:30, recompensas de "
        "indicação a cada hora (UTC)"
    )


def parar_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("Scheduler encerrado")
