"""Quiz por módulo: admin edita (com gabarito), aluno responde (sem gabarito),
certificado exige passar nos quizzes."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import delete as sa_delete

from app.core.db import AsyncSessionLocal
from app.models import Matricula, Progresso, StatusMatricula, TentativaQuiz


def _quiz_body(nota_corte: int = 70):
    return {
        "titulo": "Prova do módulo",
        "nota_corte": nota_corte,
        "ativo": True,
        "questoes": [
            {
                "enunciado": "2 + 2 = ?",
                "alternativas": [
                    {"texto": "4", "correta": True},
                    {"texto": "3", "correta": False},
                ],
            },
            {
                "enunciado": "Capital do Brasil?",
                "alternativas": [
                    {"texto": "Brasília", "correta": True},
                    {"texto": "Rio", "correta": False},
                ],
            },
        ],
    }


async def _seed_curso_modulo_aula(client, admin_token):
    slug = f"quiz-{uuid.uuid4().hex[:6]}"
    c = await client.post(
        "/api/v1/admin/cursos",
        headers=admin_token,
        json={"slug": slug, "titulo": "Curso Quiz", "tipo": "premium", "preco": 0},
    )
    curso_id = c.json()["id"]
    m = await client.post(
        f"/api/v1/admin/cursos/{curso_id}/modulos",
        headers=admin_token,
        json={"titulo": "M1", "ordem": 1},
    )
    modulo_id = m.json()["id"]
    a = await client.post(
        f"/api/v1/admin/modulos/{modulo_id}/aulas",
        headers=admin_token,
        json={"titulo": "Aula 1", "ordem": 1},
    )
    return slug, curso_id, modulo_id, a.json()["id"]


async def _matricular(test_aluno, curso_id, status=StatusMatricula.ativo, dias=30):
    async with AsyncSessionLocal() as db:
        mat = Matricula(
            aluno_id=uuid.UUID(test_aluno["id"]),
            curso_id=uuid.UUID(curso_id),
            status=status,
            data_expiracao=datetime.now(timezone.utc) + timedelta(days=dias),
        )
        db.add(mat)
        await db.commit()
        return str(mat.id)


async def _limpar_matricula(mat_id: str):
    from app.models import Certificado

    async with AsyncSessionLocal() as db:
        mid = uuid.UUID(mat_id)
        await db.execute(sa_delete(TentativaQuiz).where(TentativaQuiz.matricula_id == mid))
        await db.execute(sa_delete(Progresso).where(Progresso.matricula_id == mid))
        await db.execute(sa_delete(Certificado).where(Certificado.matricula_id == mid))
        await db.execute(sa_delete(Matricula).where(Matricula.id == mid))
        await db.commit()


class TestQuizAdmin:
    async def test_upsert_exige_uma_correta(self, client: AsyncClient, admin_token: dict):
        slug, curso_id, modulo_id, _ = await _seed_curso_modulo_aula(client, admin_token)
        try:
            ruim = _quiz_body()
            ruim["questoes"][0]["alternativas"][1]["correta"] = True  # 2 corretas
            r = await client.put(
                f"/api/v1/admin/modulos/{modulo_id}/quiz",
                headers=admin_token, json=ruim,
            )
            assert r.status_code == 422
            assert r.json()["error"]["code"] == "QUESTAO_SEM_GABARITO"
        finally:
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)

    async def test_upsert_e_get(self, client: AsyncClient, admin_token: dict):
        slug, curso_id, modulo_id, _ = await _seed_curso_modulo_aula(client, admin_token)
        try:
            r = await client.put(
                f"/api/v1/admin/modulos/{modulo_id}/quiz",
                headers=admin_token, json=_quiz_body(),
            )
            assert r.status_code == 200
            assert len(r.json()["questoes"]) == 2
            # GET admin traz o gabarito
            g = await client.get(
                f"/api/v1/admin/modulos/{modulo_id}/quiz", headers=admin_token
            )
            assert any(a["correta"] for a in g.json()["questoes"][0]["alternativas"])
        finally:
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)


class TestQuizAluno:
    async def test_responde_e_gate_do_certificado(
        self, client: AsyncClient, admin_token: dict, auth_headers: dict, test_aluno: dict
    ):
        slug, curso_id, modulo_id, aula_id = await _seed_curso_modulo_aula(client, admin_token)
        quiz = (await client.put(
            f"/api/v1/admin/modulos/{modulo_id}/quiz",
            headers=admin_token, json=_quiz_body(70),
        )).json()
        quiz_id = quiz["id"]
        mat_id = await _matricular(test_aluno, curso_id)
        try:
            # aluno vê o quiz SEM gabarito
            q = (await client.get(f"/api/v1/quizzes/{quiz_id}", headers=auth_headers)).json()
            assert q["aprovado"] is False
            for quest in q["questoes"]:
                for alt in quest["alternativas"]:
                    assert "correta" not in alt
            # mapeia alternativas por texto p/ responder
            def alt_id(qi, texto):
                quest = q["questoes"][qi]
                return next(a["id"] for a in quest["alternativas"] if a["texto"] == texto)

            # responde 1 certa + 1 errada => 50% < 70 => reprovado
            r = await client.post(
                f"/api/v1/quizzes/{quiz_id}/tentativas",
                headers=auth_headers,
                json={"respostas": [
                    {"questao_id": q["questoes"][0]["id"], "alternativa_id": alt_id(0, "4")},
                    {"questao_id": q["questoes"][1]["id"], "alternativa_id": alt_id(1, "Rio")},
                ]},
            )
            assert r.status_code == 200
            assert r.json()["nota"] == 50.0 and r.json()["aprovado"] is False

            # conclui a aula (necessário para o certificado)
            await client.post(
                "/api/v1/progresso",
                headers=auth_headers,
                json={"aula_id": aula_id, "percentual": 100, "concluida": True},
            )
            # aula feita mas quiz pendente => certificado bloqueado
            cert = await client.post(f"/api/v1/certificados/{mat_id}", headers=auth_headers)
            assert cert.status_code == 409 and cert.json()["error"]["code"] == "QUIZ_PENDENTE"

            # responde tudo certo => 100% => aprovado
            r2 = await client.post(
                f"/api/v1/quizzes/{quiz_id}/tentativas",
                headers=auth_headers,
                json={"respostas": [
                    {"questao_id": q["questoes"][0]["id"], "alternativa_id": alt_id(0, "4")},
                    {"questao_id": q["questoes"][1]["id"], "alternativa_id": alt_id(1, "Brasília")},
                ]},
            )
            assert r2.json()["aprovado"] is True

            # agora o certificado é emitido
            cert2 = await client.post(f"/api/v1/certificados/{mat_id}", headers=auth_headers)
            assert cert2.status_code == 201

            # player marca o quiz como aprovado e o curso como concluído
            player = (await client.get(
                f"/api/v1/me/cursos/{slug}", headers=auth_headers
            )).json()
            assert player["concluido"] is True
            mod = player["modulos"][0]
            assert mod["quiz"]["aprovado"] is True
        finally:
            async with AsyncSessionLocal() as db:
                mid = uuid.UUID(mat_id)
                await db.execute(sa_delete(TentativaQuiz).where(TentativaQuiz.matricula_id == mid))
                await db.execute(sa_delete(Progresso).where(Progresso.matricula_id == mid))
                from app.models import Certificado
                await db.execute(sa_delete(Certificado).where(Certificado.matricula_id == mid))
                await db.execute(sa_delete(Matricula).where(Matricula.id == mid))
                await db.commit()
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)

    async def test_quiz_exige_login(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/quizzes/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_quiz_exige_matricula_ativa(
        self, client: AsyncClient, admin_token: dict, auth_headers: dict, test_aluno: dict
    ):
        """Matrícula expirada não dá acesso ao quiz (nem ver, nem responder)."""
        slug, curso_id, modulo_id, _ = await _seed_curso_modulo_aula(client, admin_token)
        quiz = (await client.put(
            f"/api/v1/admin/modulos/{modulo_id}/quiz",
            headers=admin_token, json=_quiz_body(),
        )).json()
        mat_id = await _matricular(
            test_aluno, curso_id, status=StatusMatricula.expirado, dias=-1
        )
        try:
            g = await client.get(f"/api/v1/quizzes/{quiz['id']}", headers=auth_headers)
            assert g.status_code == 403 and g.json()["error"]["code"] == "SEM_ACESSO"
            p = await client.post(
                f"/api/v1/quizzes/{quiz['id']}/tentativas",
                headers=auth_headers, json={"respostas": []},
            )
            assert p.status_code == 403
        finally:
            await _limpar_matricula(mat_id)
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)

    async def test_payload_de_respostas_gigante_rejeitado(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Lista de respostas acima do teto (50) é barrada no schema (422),
        antes de qualquer gravação no JSONB."""
        respostas = [
            {"questao_id": str(uuid.uuid4()), "alternativa_id": str(uuid.uuid4())}
            for _ in range(51)
        ]
        r = await client.post(
            f"/api/v1/quizzes/{uuid.uuid4()}/tentativas",
            headers=auth_headers, json={"respostas": respostas},
        )
        assert r.status_code == 422

    async def test_resposta_de_alternativa_estranha_nao_grava(
        self, client: AsyncClient, admin_token: dict, auth_headers: dict, test_aluno: dict
    ):
        """alternativa_id que não pertence à questão é ignorada (conta como erro)
        e não é persistida — não infla a nota nem suja o JSONB."""
        slug, curso_id, modulo_id, _ = await _seed_curso_modulo_aula(client, admin_token)
        quiz = (await client.put(
            f"/api/v1/admin/modulos/{modulo_id}/quiz",
            headers=admin_token, json=_quiz_body(70),
        )).json()
        mat_id = await _matricular(test_aluno, curso_id)
        try:
            q = (await client.get(
                f"/api/v1/quizzes/{quiz['id']}", headers=auth_headers
            )).json()
            # responde a questão 0 com um alternativa_id inventado (não é do quiz)
            r = await client.post(
                f"/api/v1/quizzes/{quiz['id']}/tentativas",
                headers=auth_headers,
                json={"respostas": [
                    {"questao_id": q["questoes"][0]["id"],
                     "alternativa_id": str(uuid.uuid4())},
                ]},
            )
            assert r.status_code == 200
            # 0 corretas (alternativa estranha ignorada) de 2 questões
            assert r.json()["corretas"] == 0 and r.json()["aprovado"] is False
        finally:
            await _limpar_matricula(mat_id)
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)

    async def test_dupla_emissao_certificado_nao_vaza_500(
        self, client: AsyncClient, admin_token: dict, auth_headers: dict, test_aluno: dict
    ):
        """Dois POSTs concorrentes de certificado: um 201 e um 409 — nunca 500."""
        slug, curso_id, modulo_id, aula_id = await _seed_curso_modulo_aula(client, admin_token)
        quiz = (await client.put(
            f"/api/v1/admin/modulos/{modulo_id}/quiz",
            headers=admin_token, json=_quiz_body(70),
        )).json()
        mat_id = await _matricular(test_aluno, curso_id)
        try:
            q = (await client.get(
                f"/api/v1/quizzes/{quiz['id']}", headers=auth_headers
            )).json()

            def alt_id(qi, texto):
                return next(
                    a["id"] for a in q["questoes"][qi]["alternativas"]
                    if a["texto"] == texto
                )

            await client.post(
                f"/api/v1/quizzes/{quiz['id']}/tentativas",
                headers=auth_headers,
                json={"respostas": [
                    {"questao_id": q["questoes"][0]["id"], "alternativa_id": alt_id(0, "4")},
                    {"questao_id": q["questoes"][1]["id"],
                     "alternativa_id": alt_id(1, "Brasília")},
                ]},
            )
            await client.post(
                "/api/v1/progresso",
                headers=auth_headers,
                json={"aula_id": aula_id, "percentual": 100, "concluida": True},
            )
            r1, r2 = await asyncio.gather(
                client.post(f"/api/v1/certificados/{mat_id}", headers=auth_headers),
                client.post(f"/api/v1/certificados/{mat_id}", headers=auth_headers),
            )
            codes = sorted([r1.status_code, r2.status_code])
            assert 500 not in codes
            assert codes.count(201) == 1  # exatamente um emitiu
            assert 409 in codes           # o outro tomou conflito limpo
        finally:
            await _limpar_matricula(mat_id)
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)


class TestQuizAdminHardening:
    async def test_questoes_vazias_rejeitado(
        self, client: AsyncClient, admin_token: dict
    ):
        """Quiz ativo sem questões travaria o certificado pra sempre → 422."""
        slug, curso_id, modulo_id, _ = await _seed_curso_modulo_aula(client, admin_token)
        try:
            body = _quiz_body()
            body["questoes"] = []
            r = await client.put(
                f"/api/v1/admin/modulos/{modulo_id}/quiz",
                headers=admin_token, json=body,
            )
            assert r.status_code == 422
        finally:
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)

    async def test_excluir_quiz_com_tentativas_bloqueia(
        self, client: AsyncClient, admin_token: dict, auth_headers: dict, test_aluno: dict
    ):
        """Excluir o quiz cascatearia as tentativas dos alunos → travado em 409."""
        slug, curso_id, modulo_id, _ = await _seed_curso_modulo_aula(client, admin_token)
        quiz = (await client.put(
            f"/api/v1/admin/modulos/{modulo_id}/quiz",
            headers=admin_token, json=_quiz_body(),
        )).json()
        mat_id = await _matricular(test_aluno, curso_id)
        try:
            q = (await client.get(
                f"/api/v1/quizzes/{quiz['id']}", headers=auth_headers
            )).json()
            await client.post(
                f"/api/v1/quizzes/{quiz['id']}/tentativas",
                headers=auth_headers,
                json={"respostas": [
                    {"questao_id": q["questoes"][0]["id"],
                     "alternativa_id": q["questoes"][0]["alternativas"][0]["id"]},
                ]},
            )
            d = await client.delete(
                f"/api/v1/admin/modulos/{modulo_id}/quiz", headers=admin_token
            )
            assert d.status_code == 409
            assert d.json()["error"]["code"] == "QUIZ_COM_TENTATIVAS"
        finally:
            await _limpar_matricula(mat_id)
            await client.delete(f"/api/v1/admin/cursos/{curso_id}", headers=admin_token)
