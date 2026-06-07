"""Job de limpeza de refresh_tokens: remove vencidos e revogados antigos,
preserva válidos e revogados recentes (janela de detecção de reuso)."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.core.scheduler import REFRESH_RETENCAO_REVOGADOS_DIAS, limpar_refresh_tokens
from app.models import RefreshToken


class TestLimpezaRefreshTokens:
    async def test_remove_vencidos_e_revogados_antigos(self, test_aluno: dict):
        aluno_id = uuid.UUID(test_aluno["id"])
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            valido = RefreshToken(
                aluno_id=aluno_id, jti=uuid.uuid4(),
                expira_em=now + timedelta(days=7),
            )
            vencido = RefreshToken(
                aluno_id=aluno_id, jti=uuid.uuid4(),
                expira_em=now - timedelta(days=1),
            )
            revogado_antigo = RefreshToken(
                aluno_id=aluno_id, jti=uuid.uuid4(),
                expira_em=now + timedelta(days=7),
                revogado=True,
                revogado_em=now - timedelta(days=REFRESH_RETENCAO_REVOGADOS_DIAS + 1),
            )
            revogado_recente = RefreshToken(
                aluno_id=aluno_id, jti=uuid.uuid4(),
                expira_em=now + timedelta(days=7),
                revogado=True,
                revogado_em=now - timedelta(days=1),
            )
            db.add_all([valido, vencido, revogado_antigo, revogado_recente])
            await db.commit()
            jtis = {
                "valido": valido.jti,
                "vencido": vencido.jti,
                "revogado_antigo": revogado_antigo.jti,
                "revogado_recente": revogado_recente.jti,
            }

            removidos = await limpar_refresh_tokens(db)
            assert removidos >= 2  # ao menos os dois que criamos para sair

            restantes = set(
                (
                    await db.execute(
                        select(RefreshToken.jti).where(
                            RefreshToken.jti.in_(list(jtis.values()))
                        )
                    )
                ).scalars().all()
            )

            assert jtis["valido"] in restantes
            assert jtis["revogado_recente"] in restantes
            assert jtis["vencido"] not in restantes
            assert jtis["revogado_antigo"] not in restantes

            # cleanup dos tokens de teste
            await db.execute(
                delete(RefreshToken).where(
                    RefreshToken.jti.in_(list(jtis.values()))
                )
            )
            await db.commit()
