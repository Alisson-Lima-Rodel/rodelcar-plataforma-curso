"""Notificações de vigência — modo fake (dev) não dispara envio real, mas
exercita todo o pipeline: persistência, status e idempotência."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.notificacoes import MensagemNotificacao, enviar_email, enviar_whatsapp
from app.core.scheduler import _processar_notificacao
from app.core.security import hash_password
from app.models import (
    Aluno,
    CanalNotificacao,
    Curso,
    Matricula,
    Notificacao,
    StatusMatricula,
    StatusNotificacao,
    TipoCurso,
    TipoNotificacao,
)


def _msg(tel: str | None = None) -> MensagemNotificacao:
    return MensagemNotificacao(
        aluno_nome="João Silva",
        aluno_email="joao@example.com",
        aluno_telefone=tel,
        tipo=TipoNotificacao.vigencia_expirada,
        marco="expirado",
        curso_titulo="Curso X",
        data_expiracao=datetime.now(timezone.utc),
    )


class TestModoFake:
    async def test_email_fake_retorna_id_sem_enviar(self, monkeypatch):
        monkeypatch.setattr(settings, "NOTIFICACOES_FAKE", True)
        monkeypatch.setattr(settings, "SMTP_HOST", "")  # prova que não usa SMTP
        pid = await enviar_email(_msg())
        assert pid is not None and pid.startswith("fake-email-")

    async def test_whatsapp_fake_com_telefone(self, monkeypatch):
        monkeypatch.setattr(settings, "NOTIFICACOES_FAKE", True)
        monkeypatch.setattr(settings, "WA_PROVIDER", "")  # prova que não usa provider
        pid = await enviar_whatsapp(_msg(tel="+55 11 99999-0000"))
        assert pid is not None and pid.startswith("fake-wa-")

    async def test_whatsapp_sem_telefone_retorna_none(self, monkeypatch):
        monkeypatch.setattr(settings, "NOTIFICACOES_FAKE", True)
        assert await enviar_whatsapp(_msg(tel=None)) is None


class TestPipelineFake:
    async def test_processa_persiste_enviada_e_e_idempotente(self, monkeypatch):
        monkeypatch.setattr(settings, "NOTIFICACOES_FAKE", True)
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            aluno = Aluno(
                nome="Fake Tester",
                email=f"fake_{uuid.uuid4().hex[:8]}@example.com",
                senha_hash=hash_password("x"),
                telefone="+5511999990000",
            )
            db.add(aluno)
            await db.flush()
            curso = Curso(
                slug=f"fake-{uuid.uuid4().hex[:6]}",
                titulo="Curso Fake",
                tipo=TipoCurso.avulso,
                preco=10,
                validade_dias=30,
            )
            db.add(curso)
            await db.flush()
            mat = Matricula(
                aluno_id=aluno.id,
                curso_id=curso.id,
                status=StatusMatricula.expirado,
                data_expiracao=now - timedelta(days=1),
            )
            db.add(mat)
            await db.flush()

            mat_full = (
                await db.execute(
                    select(Matricula)
                    .where(Matricula.id == mat.id)
                    .options(
                        selectinload(Matricula.aluno), selectinload(Matricula.curso)
                    )
                )
            ).scalar_one()

            try:
                nova, ok = await _processar_notificacao(
                    db, mat_full, TipoNotificacao.vigencia_expirada,
                    CanalNotificacao.email, "expirado", now, dry_run=False,
                )
                assert nova is True and ok is True

                row = (
                    await db.execute(
                        select(Notificacao).where(Notificacao.matricula_id == mat.id)
                    )
                ).scalar_one()
                assert row.status == StatusNotificacao.enviada
                assert row.provedor_msg_id.startswith("fake-email-")
                assert row.enviada_em is not None

                # 2ª passada: idempotência pela chave única — não duplica.
                nova2, _ = await _processar_notificacao(
                    db, mat_full, TipoNotificacao.vigencia_expirada,
                    CanalNotificacao.email, "expirado", now, dry_run=False,
                )
                assert nova2 is False
            finally:
                await db.execute(
                    delete(Notificacao).where(Notificacao.matricula_id == mat.id)
                )
                await db.execute(delete(Matricula).where(Matricula.id == mat.id))
                await db.execute(delete(Curso).where(Curso.id == curso.id))
                await db.execute(delete(Aluno).where(Aluno.id == aluno.id))
                await db.commit()
