import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Matricula, StatusMatricula


async def checar_vigencia_aluno(aluno_id: uuid.UUID, db: AsyncSession) -> None:
    """Marca como expirado matrículas ativas com data_expiracao vencida."""
    agora = datetime.now(timezone.utc)
    await db.execute(
        update(Matricula)
        .where(
            Matricula.aluno_id == aluno_id,
            Matricula.status == StatusMatricula.ativo,
            Matricula.data_expiracao < agora,
        )
        .values(status=StatusMatricula.expirado)
    )
    await db.commit()
