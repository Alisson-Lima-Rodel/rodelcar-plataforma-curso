"""Semeia um aluno de teste com matrícula + progresso (para ver a Área do Aluno).

Uso:
    docker compose run --rm --entrypoint python backend -m scripts.seed_aluno

Idempotente: se o e-mail já existir, não faz nada. Requer os cursos seedados
(scripts.seed) — usa o curso 'dualogic'.

    Login de teste:  aluno@teste.com  /  Aluno123!
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models import Aluno, Aula, Curso, Matricula, Modulo, Progresso, StatusMatricula

EMAIL = "aluno@teste.com"
SENHA = "Aluno123!"


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, connect_args=settings.db_connect_args)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as s:
        if await s.scalar(select(Aluno.id).where(Aluno.email == EMAIL)):
            print(f"= {EMAIL} já existe, nada a fazer.")
            await engine.dispose()
            return

        curso = (await s.execute(select(Curso).where(Curso.slug == "dualogic"))).scalar_one_or_none()
        if curso is None:
            print("! curso 'dualogic' não encontrado — rode `scripts.seed` antes.")
            await engine.dispose()
            return

        aluno = Aluno(nome="Rogério Alves", email=EMAIL, senha_hash=hash_password(SENHA))
        s.add(aluno)
        await s.flush()

        agora = datetime.now(timezone.utc)
        mat = Matricula(
            aluno_id=aluno.id,
            curso_id=curso.id,
            status=StatusMatricula.ativo,
            data_expiracao=agora + timedelta(days=12),  # ≤15 dias → dispara alerta de vigência
        )
        s.add(mat)
        await s.flush()

        aulas = (
            await s.execute(
                select(Aula)
                .join(Modulo, Aula.modulo_id == Modulo.id)
                .where(Modulo.curso_id == curso.id)
                .order_by(Modulo.ordem, Aula.ordem)
            )
        ).scalars().all()
        for a in aulas[:6]:
            s.add(Progresso(matricula_id=mat.id, aula_id=a.id, concluida=True, percentual=100))

        await s.commit()
        print(f"+ aluno {EMAIL} (senha {SENHA}) | matrícula em '{curso.slug}' | {min(6, len(aulas))} aulas concluídas")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
