import uuid

from httpx import AsyncClient
from sqlalchemy import update

from app.core.db import AsyncSessionLocal
from app.models import Progresso


# ── POST /api/v1/progresso ────────────────────────────────────────────────────
class TestProgresso:
    async def test_salva_progresso_retorna_200(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.post(
            "/api/v1/progresso",
            json={
                "aula_id": test_data["aula_ativa_id"],
                "percentual": 60,
                "concluida": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["aula_id"] == test_data["aula_ativa_id"]
        assert data["percentual"] == 60
        assert data["concluida"] is False
        assert "curso_percentual" in data
        # Curso tem 1 aula com 60 % → curso_percentual == 60.0
        assert data["curso_percentual"] == 60.0

    async def test_upsert_atualiza_percentual(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Segunda chamada com mesma aula deve fazer upsert, não criar duplicata."""
        await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 30, "concluida": False},
            headers=auth_headers,
        )
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 85, "concluida": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["percentual"] == 85

    async def test_curso_percentual_100_quando_aula_concluida(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Marcar aula como concluída (100 %) → curso_percentual == 100.0."""
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 100, "concluida": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["curso_percentual"] == 100.0

    async def test_progresso_sem_matricula_retorna_404(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Sem matrícula no curso → 404 (igual a aula inexistente; anti-enumeração)."""
        resp = await client.post(
            "/api/v1/progresso",
            json={
                "aula_id": test_data["aula_sem_mat_id"],
                "percentual": 50,
                "concluida": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "AULA_NAO_ENCONTRADA"

    async def test_progresso_aula_inexistente_retorna_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": str(uuid.uuid4()), "percentual": 50, "concluida": False},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_progresso_sem_token_retorna_401(
        self, client: AsyncClient, test_data: dict
    ):
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 50, "concluida": False},
        )
        assert resp.status_code == 401

    async def test_progresso_percentual_invalido_retorna_422(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.post(
            "/api/v1/progresso",
            json={"aula_id": test_data["aula_ativa_id"], "percentual": 150, "concluida": False},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_percentual_monotonico_nao_regride(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Ping com percentual MENOR não regride o progresso já alcançado (greatest)."""
        aula = test_data["aula_ativa_id"]
        r1 = await client.post(
            "/api/v1/progresso",
            json={"aula_id": aula, "percentual": 90, "concluida": False},
            headers=auth_headers,
        )
        assert r1.status_code == 200
        p1 = r1.json()["percentual"]
        assert p1 >= 90  # >= por causa de possível estado anterior do test_data
        r2 = await client.post(
            "/api/v1/progresso",
            json={"aula_id": aula, "percentual": 5, "concluida": False},
            headers=auth_headers,
        )
        assert r2.status_code == 200
        assert r2.json()["percentual"] == p1  # não regrediu


# ── POST + GET /api/v1/certificados ──────────────────────────────────────────
class TestCertificados:
    async def test_sem_conclusao_retorna_409(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Sem progresso → não pode emitir certificado (409 CURSO_NAO_CONCLUIDO)."""
        resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CURSO_NAO_CONCLUIDO"

    async def test_matricula_expirada_nao_emite_409(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Matrícula não-ativa (expirada/revogada) não emite certificado — senão um
        aluno estornado geraria prova de conclusão falsa."""
        resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_expirada_id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "MATRICULA_NAO_ATIVA"

    async def test_fluxo_completo_emitir_e_verificar(
        self, client: AsyncClient, auth_headers: dict, test_data: dict, monkeypatch
    ):
        """Conclui a única aula → emite certificado → verifica código publicamente."""
        # Grava o e-mail de certificado disparado na emissão (best-effort).
        import app.routers.certificados as cert_router

        emails: list[str] = []

        async def fake_email(para, assunto, corpo, *, log_ref="?"):
            emails.append(assunto)
            return "fake-id"

        monkeypatch.setattr(cert_router, "enviar_email_bruto", fake_email)

        # 1. Marca aula_cert como 100 % concluída
        prog_resp = await client.post(
            "/api/v1/progresso",
            json={
                "aula_id": test_data["aula_cert_id"],
                "percentual": 100,
                "concluida": True,
            },
            headers=auth_headers,
        )
        assert prog_resp.status_code == 200
        assert prog_resp.json()["curso_percentual"] == 100.0

        # Acumula tempo assistido suficiente p/ o gate anti-fraude (aula_cert agora
        # tem duracao=60; o gate exige segundos_assistidos >= 0.85*60). Setamos
        # direto no banco em vez de simular vários pings com relógio real.
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Progresso)
                .where(Progresso.aula_id == uuid.UUID(test_data["aula_cert_id"]))
                .values(segundos_assistidos=60)
            )
            await db.commit()

        # 2. Emite certificado
        cert_resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}",
            headers=auth_headers,
        )
        assert cert_resp.status_code == 201
        cert = cert_resp.json()
        # E-mail de certificado foi disparado na emissão
        assert len(emails) == 1 and "certificado" in emails[0].lower()
        assert "id" in cert
        assert "codigo_verificacao" in cert
        assert "emitido_em" in cert
        codigo = cert["codigo_verificacao"]
        assert codigo.startswith("RC-")
        assert len(codigo) == 24  # RC-YYYY-XXXXXXXXXXXXXXXX (2+1+4+1+16), não enumerável

        # Armazena o código para o teste seguinte
        test_data["_codigo_cert"] = codigo

        # 3. Verifica o código publicamente (sem autenticação)
        verify_resp = await client.get(f"/api/v1/certificados/{codigo}/verificar")
        assert verify_resp.status_code == 200
        v = verify_resp.json()
        assert v["valido"] is True
        assert isinstance(v["aluno_nome"], str) and len(v["aluno_nome"]) > 0
        assert isinstance(v["curso"], str) and len(v["curso"]) > 0
        assert "emitido_em" in v

    async def test_baixar_pdf_retorna_200(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Com certificado emitido → GET /pdf devolve um PDF de verdade."""
        resp = await client.get(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}/pdf",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:5] == b"%PDF-"
        assert "attachment" in resp.headers.get("content-disposition", "")

    async def test_enviar_whatsapp_sem_telefone_retorna_422(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Aluno sem telefone cadastrado → 422 (mas o certificado existe)."""
        resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}/enviar-whatsapp",
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "TELEFONE_AUSENTE"

    async def test_pdf_sem_certificado_retorna_404(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Matrícula sem certificado emitido → 404 CERTIFICADO_NAO_EMITIDO."""
        resp = await client.get(
            f"/api/v1/certificados/{test_data['matricula_ativa_id']}/pdf",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CERTIFICADO_NAO_EMITIDO"

    async def test_pdf_matricula_alheia_retorna_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get(
            f"/api/v1/certificados/{uuid.uuid4()}/pdf", headers=auth_headers
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "MATRICULA_NAO_ENCONTRADA"

    async def test_pdf_sem_token_retorna_401(
        self, client: AsyncClient, test_data: dict
    ):
        resp = await client.get(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}/pdf"
        )
        assert resp.status_code == 401

    async def test_certificado_duplicado_retorna_409(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        """Emitir certificado para a mesma matrícula novamente → 409."""
        resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}",
            headers=auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CERTIFICADO_JA_EMITIDO"

    async def test_verificar_codigo_inexistente_retorna_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/certificados/RC-0000-ZZZZZZ/verificar")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "CERTIFICADO_NAO_ENCONTRADO"

    async def test_emitir_sem_token_retorna_401(
        self, client: AsyncClient, test_data: dict
    ):
        resp = await client.post(
            f"/api/v1/certificados/{test_data['matricula_cert_id']}"
        )
        assert resp.status_code == 401

    async def test_emitir_matricula_alheia_retorna_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            f"/api/v1/certificados/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "MATRICULA_NAO_ENCONTRADA"


# ── Envio de WhatsApp com texto livre (base reusável) ─────────────────────────
class TestEnviarWhatsappTexto:
    async def test_sem_telefone_retorna_none(self):
        from app.core.notificacoes import enviar_whatsapp_texto

        assert await enviar_whatsapp_texto(None, "oi") is None
        assert await enviar_whatsapp_texto("", "oi") is None

    async def test_modo_fake_retorna_id(self, monkeypatch):
        from app.core import notificacoes

        monkeypatch.setattr(notificacoes.settings, "NOTIFICACOES_FAKE", True)
        msg_id = await notificacoes.enviar_whatsapp_texto("5551999990000", "oi")
        assert msg_id is not None and msg_id.startswith("fake-wa-")

    async def test_sem_provider_retorna_none(self, monkeypatch):
        from app.core import notificacoes

        monkeypatch.setattr(notificacoes.settings, "NOTIFICACOES_FAKE", False)
        monkeypatch.setattr(notificacoes.settings, "WA_PROVIDER", "")
        assert await notificacoes.enviar_whatsapp_texto("5551999990000", "oi") is None


# ── E-mails transacionais (escaping anti-injeção) ─────────────────────────────
class TestEmailTransacional:
    def test_escapa_html_no_corpo(self):
        from app.core.email_transacional import email_compra_avulsa

        assunto, corpo = email_compra_avulsa("<script>evil</script>", "Curso <b>X</b>")
        assert "<script>" not in corpo
        assert "<b>X</b>" not in corpo
        assert "&lt;" in corpo  # foi escapado
        assert "Compra confirmada" in assunto

    def test_certificado_inclui_link(self):
        from app.core.email_transacional import email_certificado

        url = "https://rodelcar.com.br/verificar/RC-2026-ABC"
        _assunto, corpo = email_certificado("Maria", "Curso DSG", url)
        assert url in corpo
