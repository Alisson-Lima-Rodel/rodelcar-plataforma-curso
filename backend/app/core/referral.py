"""Indique-e-ganhe: código pessoal + recompensa (cupom para indicador e indicado).

Quando a indicação vira compra (webhook marca `compra_confirmada`), geramos um
cupom de desconto para CADA um (reaproveita o Stripe Coupon/Promotion Code). A
geração é best-effort fora da transação de pagamento — falha não derruba a compra.
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.exc import IntegrityError

from app.core.stripe_coupons import (
    arquivar_cupom_stripe,
    criar_cupom_stripe,
    stripe_ativo,
)
from app.models import Aluno, Cupom, Indicacao

logger = logging.getLogger(__name__)

# Recompensa: cupom de 10% OFF para ambos, válido por 90 dias, 1 uso.
RECOMPENSA_PCT = 10.0
RECOMPENSA_VALIDADE_DIAS = 90
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem caracteres ambíguos


def gerar_codigo(prefixo: str = "") -> str:
    """Código curto não-ambíguo (ex.: 'RC7K2QF9' ou 'INDICA-7K2QF9')."""
    corpo = "".join(secrets.choice(_ALFABETO) for _ in range(8))
    return f"{prefixo}{corpo}"


async def codigo_unico_indicacao(db: AsyncSession) -> str:
    """Gera um código pessoal garantidamente livre na tabela de alunos."""
    for _ in range(10):
        codigo = gerar_codigo()
        existe = await db.scalar(
            select(Aluno.id).where(Aluno.codigo_indicacao == codigo)
        )
        if not existe:
            return codigo
    return gerar_codigo() + secrets.token_hex(2).upper()  # praticamente impossível


async def _cupom_recompensa(
    db: AsyncSession, aluno_id: uuid.UUID, promos_criados: list[str]
) -> Cupom | None:
    """Cria 1 cupom de recompensa (Stripe + banco) para um aluno. Registra o
    promotion_code em `promos_criados` p/ o caller arquivar se algo falhar depois.
    None se a Stripe falhar."""
    codigo = gerar_codigo("INDICA-")
    validade = datetime.now(timezone.utc) + timedelta(days=RECOMPENSA_VALIDADE_DIAS)
    try:
        coupon_id, promo_id = await criar_cupom_stripe(
            codigo, "percentual", RECOMPENSA_PCT,
            max_resgates=1, validade_ts=int(validade.timestamp()),
        )
    except Exception:
        logger.exception("Falha ao criar cupom de indicação na Stripe (aluno=%s)", aluno_id)
        return None
    promos_criados.append(promo_id)
    cupom = Cupom(
        codigo=codigo,
        descricao="Recompensa indique-e-ganhe",
        tipo="percentual",
        valor=RECOMPENSA_PCT,
        stripe_coupon_id=coupon_id,
        stripe_promotion_code_id=promo_id,
        max_resgates=1,
        validade=validade,
        aluno_id=aluno_id,
    )
    db.add(cupom)
    return cupom


async def processar_recompensa(db: AsyncSession, indicacao_id: uuid.UUID) -> bool:
    """Gera os cupons de AMBOS e marca a indicação como recompensada. Idempotente
    (só age em status='compra_confirmada'). Best-effort: sem Stripe, não faz nada.
    Em falha (Stripe down, colisão de código), arquiva os cupons já criados na
    Stripe (sem órfãos) e deixa a indicação em 'compra_confirmada' p/ o job retomar."""
    indicacao = await db.get(Indicacao, indicacao_id)
    if indicacao is None or indicacao.status != "compra_confirmada":
        return False
    if not stripe_ativo():
        logger.info("Stripe inativo — recompensa de indicação adiada (%s).", indicacao_id)
        return False

    promos_criados: list[str] = []
    try:
        cupom_ind = await _cupom_recompensa(db, indicacao.indicador_id, promos_criados)
        cupom_indicado = await _cupom_recompensa(db, indicacao.indicado_id, promos_criados)
        if cupom_ind is None or cupom_indicado is None:
            raise RuntimeError("cupom de recompensa nao criado")
        await db.flush()  # colisão de código (improvável) -> IntegrityError aqui
        indicacao.cupom_indicador_id = cupom_ind.id
        indicacao.cupom_indicado_id = cupom_indicado.id
        indicacao.status = "recompensado"
        indicacao.recompensado_em = datetime.now(timezone.utc)
        await db.commit()
        return True
    except (IntegrityError, RuntimeError, Exception):
        await db.rollback()
        # Arquiva na Stripe os cupons que chegaram a ser criados (evita órfãos).
        for promo_id in promos_criados:
            await arquivar_cupom_stripe(promo_id)
        logger.warning("Recompensa da indicação %s adiada (sera retentada).", indicacao_id)
        return False


async def processar_recompensas_pendentes(db: AsyncSession, limite: int = 100) -> int:
    """Retoma recompensas presas em 'compra_confirmada' (ex.: Stripe fora no
    webhook). Idempotente. Roda no scheduler. Retorna quantas foram recompensadas."""
    ids = (
        await db.execute(
            select(Indicacao.id)
            .where(Indicacao.status == "compra_confirmada")
            .limit(limite)
        )
    ).scalars().all()
    feitas = 0
    for indicacao_id in ids:
        if await processar_recompensa(db, indicacao_id):
            feitas += 1
    return feitas
