"""Matrícula gratuita: aluno cadastrado entra em curso marcado como gratuito."""
import uuid

from httpx import AsyncClient


class TestMatriculaGratis:
    async def test_curso_nao_gratuito_403(
        self, client: AsyncClient, auth_headers: dict, test_data: dict
    ):
        resp = await client.post(
            f"/api/v1/me/matriculas/gratis/{test_data['curso_ativo_slug']}",
            headers=auth_headers,
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "CURSO_NAO_GRATUITO"

    async def test_curso_inexistente_404(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/me/matriculas/gratis/nao-existe-xyz", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_sem_token_401(self, client: AsyncClient, test_data: dict):
        resp = await client.post(
            f"/api/v1/me/matriculas/gratis/{test_data['curso_ativo_slug']}"
        )
        assert resp.status_code == 401

    async def test_matricula_gratis_e_idempotencia(
        self, client: AsyncClient, admin_token: dict, auth_headers: dict, test_aluno: dict
    ):
        from sqlalchemy import delete as sa_delete

        from app.core.db import AsyncSessionLocal
        from app.models import Matricula

        slug = f"free-{uuid.uuid4().hex[:6]}"
        # curso gratuito (premium evita sync Stripe)
        c = await client.post(
            "/api/v1/admin/cursos",
            headers=admin_token,
            json={
                "slug": slug, "titulo": "Curso Grátis", "tipo": "premium",
                "preco": 0, "gratuito": True,
            },
        )
        assert c.status_code == 201
        assert c.json()["gratuito"] is True
        curso_id = c.json()["id"]
        try:
            # 1ª matrícula → nova
            r1 = await client.post(
                f"/api/v1/me/matriculas/gratis/{slug}", headers=auth_headers
            )
            assert r1.status_code == 201
            d1 = r1.json()
            assert d1["status"] == "ativo" and d1["ja_matriculado"] is False

            # detalhe público expõe gratuito=true
            det = (await client.get(f"/api/v1/cursos/{slug}")).json()
            assert det["gratuito"] is True

            # 2ª chamada → idempotente (reativa), ja_matriculado=true
            r2 = await client.post(
                f"/api/v1/me/matriculas/gratis/{slug}", headers=auth_headers
            )
            assert r2.status_code == 201
            assert r2.json()["ja_matriculado"] is True

            # aparece em /me/matriculas como ativo
            mats = (
                await client.get("/api/v1/me/matriculas", headers=auth_headers)
            ).json()
            assert any(
                m["curso"]["slug"] == slug and m["status"] == "ativo"
                for m in mats["items"]
            )
        finally:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_delete(Matricula).where(
                        Matricula.curso_id == uuid.UUID(curso_id)
                    )
                )
                await db.commit()
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)
