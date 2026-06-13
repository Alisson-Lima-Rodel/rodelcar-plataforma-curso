"""Gestão de módulo/aula no admin + preview público da aula grátis."""
import uuid

from httpx import AsyncClient


class TestConteudoAdmin:
    async def test_fluxo_completo_e_preview(
        self, client: AsyncClient, admin_token: dict
    ):
        slug = f"prev-{uuid.uuid4().hex[:6]}"
        # 1. cria curso (premium evita sync Stripe)
        c = await client.post(
            "/api/v1/admin/cursos",
            headers=admin_token,
            json={"slug": slug, "titulo": "Curso Preview", "tipo": "premium", "preco": 0},
        )
        assert c.status_code == 201
        curso_id = c.json()["id"]

        try:
            # 2. cria módulo
            m = await client.post(
                f"/api/v1/admin/cursos/{curso_id}/modulos",
                headers=admin_token,
                json={"titulo": "Módulo 1", "ordem": 1},
            )
            assert m.status_code == 201
            modulo_id = m.json()["id"]

            # 3. cria aula paga + aula grátis
            paga = await client.post(
                f"/api/v1/admin/modulos/{modulo_id}/aulas",
                headers=admin_token,
                json={"titulo": "Aula paga", "panda_video_id": "PAGA123", "ordem": 1},
            )
            gratis = await client.post(
                f"/api/v1/admin/modulos/{modulo_id}/aulas",
                headers=admin_token,
                json={
                    "titulo": "Aula grátis",
                    "panda_video_id": "FREE456",
                    "ordem": 2,
                    "gratuita": True,
                },
            )
            assert paga.status_code == 201 and gratis.status_code == 201
            assert gratis.json()["gratuita"] is True

            # 4. admin lista o conteúdo (árvore)
            cont = await client.get(
                f"/api/v1/admin/cursos/{curso_id}/conteudo", headers=admin_token
            )
            assert cont.status_code == 200
            mods = cont.json()
            assert len(mods) == 1 and len(mods[0]["aulas"]) == 2

            # 5. preview público: SÓ a grátis, e a paga NUNCA vaza o video id
            prev = await client.get(f"/api/v1/cursos/{slug}/preview")
            assert prev.status_code == 200
            pv = prev.json()
            assert len(pv) == 1 and pv[0]["panda_video_id"] == "FREE456"
            assert all(x["panda_video_id"] != "PAGA123" for x in pv)

            # 6. detalhe expõe a flag gratuita por aula (sem panda_video_id)
            det = (await client.get(f"/api/v1/cursos/{slug}")).json()
            aulas = det["modulos"][0]["aulas"]
            assert any(a["gratuita"] for a in aulas)
            assert any(not a["gratuita"] for a in aulas)
            assert all("panda_video_id" not in a for a in aulas)

            # 7. vitrine: tem_preview = true
            lst = (await client.get("/api/v1/cursos?size=100")).json()
            item = next(i for i in lst["items"] if i["slug"] == slug)
            assert item["tem_preview"] is True

            # 8. desmarcar a grátis some do preview
            await client.patch(
                f"/api/v1/admin/aulas/{gratis.json()['id']}",
                headers=admin_token,
                json={"gratuita": False},
            )
            assert (await client.get(f"/api/v1/cursos/{slug}/preview")).json() == []

            # 9. excluir o módulo (cascata nas aulas)
            d = await client.delete(
                f"/api/v1/admin/modulos/{modulo_id}", headers=admin_token
            )
            assert d.status_code == 204
            cont2 = await client.get(
                f"/api/v1/admin/cursos/{curso_id}/conteudo", headers=admin_token
            )
            assert cont2.json() == []
        finally:
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)

    async def test_conteudo_exige_admin(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            f"/api/v1/admin/cursos/{uuid.uuid4()}/conteudo", headers=auth_headers
        )
        assert resp.status_code in (401, 403)

    async def test_preview_curso_inexistente_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/cursos/nao-existe-xyz/preview")
        assert resp.status_code == 404
