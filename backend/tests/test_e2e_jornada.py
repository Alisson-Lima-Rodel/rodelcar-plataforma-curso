"""E2E da jornada do aluno contra a app real + banco real.

Exercita a sequência completa — cadastro → login → refresh (rotação + anti-roubo)
→ matrícula grátis → acesso → progresso (anti-fraude) → gates do certificado →
quiz (reprova/aprova) → certificado → verificação → avaliação — e CONFERE cada
gravação no banco. Curso isolado criado/derrubado pela fixture; aluno criado via
API e limpo no teardown.

Roda contra o Supabase real (como o resto da suíte). Marcado para poder pular em
ambiente sem banco: `pytest -m "not e2e"`.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, func, select, update

from app.core.db import AsyncSessionLocal
from app.core.ratelimit import limiter
from app.models import (
    Alternativa,
    Aluno,
    Aula,
    Avaliacao,
    Certificado,
    Curso,
    Evento,
    Matricula,
    Modulo,
    Progresso,
    Questao,
    Quiz,
    StatusCurso,
    StatusMatricula,
    TentativaQuiz,
    TipoCurso,
)

pytestmark = pytest.mark.e2e

SENHA = "E2EPass123!"
DUR = 60  # duracao_segundos por aula → gate do certificado = 0.85 * 60 = 51s


@pytest_asyncio.fixture
async def curso_e2e():
    """Curso GRATUITO isolado: 1 módulo, 2 aulas (dur=60s), 1 quiz (2 questões).
    Devolve ids + e-mail do aluno de teste + gabarito. Limpa tudo no teardown."""
    pref = uuid.uuid4().hex[:8]
    email = f"e2e_{pref}@rodelcar.dev"
    async with AsyncSessionLocal() as db:
        curso = Curso(
            slug=f"e2e-{pref}", titulo="E2E Curso", tipo=TipoCurso.avulso,
            preco=0, validade_dias=365, gratuito=True, status=StatusCurso.ativo,
        )
        db.add(curso)
        await db.flush()
        mod = Modulo(curso_id=curso.id, titulo="Módulo E2E", ordem=1)
        db.add(mod)
        await db.flush()
        a1 = Aula(modulo_id=mod.id, titulo="Aula 1", ordem=1, duracao_segundos=DUR)
        a2 = Aula(modulo_id=mod.id, titulo="Aula 2", ordem=2, duracao_segundos=DUR)
        db.add_all([a1, a2])
        await db.flush()
        quiz = Quiz(modulo_id=mod.id, titulo="Quiz E2E", nota_corte=70, ativo=True)
        db.add(quiz)
        await db.flush()
        questoes = []
        for i in range(2):
            q = Questao(quiz_id=quiz.id, enunciado=f"Pergunta {i + 1}?", ordem=i)
            db.add(q)
            await db.flush()
            certa = Alternativa(questao_id=q.id, texto="Certa", correta=True, ordem=0)
            errada = Alternativa(questao_id=q.id, texto="Errada", correta=False, ordem=1)
            db.add_all([certa, errada])
            await db.flush()
            questoes.append({"q": str(q.id), "certa": str(certa.id), "errada": str(errada.id)})
        await db.commit()
        ids = {
            "curso_id": curso.id, "mod_id": mod.id, "a1": a1.id, "a2": a2.id,
            "quiz_id": quiz.id, "slug": curso.slug, "email": email, "questoes": questoes,
        }

    yield ids

    # Teardown: aluno (se criado) + curso, em ordem de FK.
    async with AsyncSessionLocal() as db:
        al = (await db.execute(select(Aluno).where(Aluno.email == email))).scalar_one_or_none()
        if al:
            mats = (await db.execute(select(Matricula.id).where(Matricula.aluno_id == al.id))).scalars().all()
            await db.execute(delete(Certificado).where(Certificado.matricula_id.in_(mats)))
            await db.execute(delete(TentativaQuiz).where(TentativaQuiz.matricula_id.in_(mats)))
            await db.execute(delete(Progresso).where(Progresso.matricula_id.in_(mats)))
            await db.execute(delete(Avaliacao).where(Avaliacao.aluno_id == al.id))
            await db.execute(delete(Matricula).where(Matricula.aluno_id == al.id))
            await db.execute(delete(Evento).where(Evento.aluno_id == al.id))
        qs = (await db.execute(select(Questao.id).where(Questao.quiz_id == ids["quiz_id"]))).scalars().all()
        await db.execute(delete(Alternativa).where(Alternativa.questao_id.in_(qs)))
        await db.execute(delete(Questao).where(Questao.quiz_id == ids["quiz_id"]))
        await db.execute(delete(Quiz).where(Quiz.id == ids["quiz_id"]))
        await db.execute(delete(Aula).where(Aula.modulo_id == ids["mod_id"]))
        await db.execute(delete(Modulo).where(Modulo.id == ids["mod_id"]))
        await db.execute(delete(Curso).where(Curso.id == ids["curso_id"]))
        if al:
            obj = await db.get(Aluno, al.id)
            if obj:
                await db.delete(obj)  # cascade: refresh_tokens, indicacoes
        await db.commit()


async def _backdate(matricula_id, aula_id, segs=31):
    """Retroage atualizado_em para o próximo ping creditar tempo (simula real)."""
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Progresso)
            .where(Progresso.matricula_id == matricula_id, Progresso.aula_id == aula_id)
            .values(atualizado_em=datetime.now(timezone.utc) - timedelta(seconds=segs))
        )
        await db.commit()


async def _assistir(client, headers, matricula_id, aula_id):
    """3 pings com backdate entre eles → ~60s acumulados + concluída."""
    for i in range(3):
        r = await client.post("/api/v1/progresso", headers=headers, json={
            "aula_id": str(aula_id),
            "percentual": 100.0 if i == 2 else 50.0,
            "concluida": i == 2,
            "posicao_segundos": 30 + i * 15,
        })
        assert r.status_code == 200, r.text
        if i < 2:
            await _backdate(matricula_id, aula_id)


async def test_jornada_completa_do_aluno(client: AsyncClient, curso_e2e: dict):
    ids = curso_e2e
    email, slug = ids["email"], ids["slug"]
    limiter.reset()

    # ── 1. CADASTRO ──────────────────────────────────────────────────────────
    r = await client.post("/api/v1/auth/register",
                          json={"nome": "Aluno E2E", "email": email, "senha": SENHA,
                                "telefone": "51999990000"})
    assert r.status_code == 201, r.text
    tok = r.json()
    assert tok.get("access_token") and tok.get("refresh_token")
    async with AsyncSessionLocal() as db:
        al = (await db.execute(select(Aluno).where(Aluno.email == email))).scalar_one()
        aluno_id = al.id
        assert al.senha_hash.startswith("$2")  # bcrypt
        assert al.codigo_indicacao  # gerado
        assert al.token_version == 0 and not al.bloqueado
        # 1 refresh token emitido no cadastro
        from app.models import RefreshToken
        assert await db.scalar(
            select(func.count(RefreshToken.id)).where(RefreshToken.aluno_id == aluno_id)
        ) == 1

    # ── 2. LOGIN ─────────────────────────────────────────────────────────────
    r = await client.post("/api/v1/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200
    refresh = r.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(Evento.id)).where(
            Evento.aluno_id == aluno_id, Evento.nome_evento == "login")) >= 1
    # senha errada → 401
    r = await client.post("/api/v1/auth/login", json={"email": email, "senha": "errada"})
    assert r.status_code == 401

    # ── 3. REFRESH (rotação + anti-roubo) ────────────────────────────────────
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    # reuso do refresh antigo → 401 e derruba sessões (bump token_version)
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401
    # re-login limpo (a detecção de roubo invalidou os tokens vivos)
    limiter.reset()
    r = await client.post("/api/v1/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # ── 4. MATRÍCULA GRÁTIS ──────────────────────────────────────────────────
    r = await client.post(f"/api/v1/me/matriculas/gratis/{slug}", headers=headers)
    assert r.status_code == 201, r.text
    async with AsyncSessionLocal() as db:
        mat = (await db.execute(select(Matricula).where(
            Matricula.aluno_id == aluno_id, Matricula.curso_id == ids["curso_id"]))).scalar_one()
        mat_id = mat.id
        assert mat.status == StatusMatricula.ativo
        assert mat.pagamento_id is None
        assert 360 <= (mat.data_expiracao - datetime.now(timezone.utc)).days <= 366

    # ── 5. ACESSO ────────────────────────────────────────────────────────────
    r = await client.get("/api/v1/me/matriculas", headers=headers)
    assert slug in [it["curso"]["slug"] for it in r.json()["items"]]
    r = await client.get(f"/api/v1/me/cursos/{slug}", headers=headers)
    assert r.status_code == 200
    estrutura = r.json()
    assert sum(len(m["aulas"]) for m in estrutura["modulos"]) == 2
    assert estrutura["modulos"][0]["quiz"]
    r = await client.get(f"/api/v1/aulas/{ids['a1']}", headers=headers)
    assert r.status_code == 200
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(Evento.id)).where(
            Evento.aluno_id == aluno_id, Evento.nome_evento == "aula_assistida")) >= 1

    # ── 6. GATE: certificado sem concluir → 409 ──────────────────────────────
    r = await client.post(f"/api/v1/certificados/{mat_id}", headers=headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "CURSO_NAO_CONCLUIDO"

    # ── 7. PROGRESSO (anti-fraude) ───────────────────────────────────────────
    await _assistir(client, headers, mat_id, ids["a1"])
    await _assistir(client, headers, mat_id, ids["a2"])
    async with AsyncSessionLocal() as db:
        for aid in (ids["a1"], ids["a2"]):
            p = (await db.execute(select(Progresso).where(
                Progresso.matricula_id == mat_id, Progresso.aula_id == aid))).scalar_one()
            assert p.concluida and float(p.percentual) == 100.0
            assert p.segundos_assistidos >= 51  # anti-fraude acumulou tempo real
            assert p.posicao_segundos and p.posicao_segundos > 0

    # ── 8. GATE: quiz pendente → 409 ─────────────────────────────────────────
    r = await client.post(f"/api/v1/certificados/{mat_id}", headers=headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "QUIZ_PENDENTE"

    # ── 9. QUIZ ──────────────────────────────────────────────────────────────
    r = await client.get(f"/api/v1/quizzes/{ids['quiz_id']}", headers=headers)
    assert r.status_code == 200
    alts = [a for q in r.json()["questoes"] for a in q["alternativas"]]
    assert all("correta" not in a for a in alts)  # gabarito NÃO vaza
    erradas = [{"questao_id": q["q"], "alternativa_id": q["errada"]} for q in ids["questoes"]]
    r = await client.post(f"/api/v1/quizzes/{ids['quiz_id']}/tentativas",
                          headers=headers, json={"respostas": erradas})
    assert r.status_code == 200 and r.json()["aprovado"] is False and float(r.json()["nota"]) == 0.0
    certas = [{"questao_id": q["q"], "alternativa_id": q["certa"]} for q in ids["questoes"]]
    r = await client.post(f"/api/v1/quizzes/{ids['quiz_id']}/tentativas",
                          headers=headers, json={"respostas": certas})
    assert r.status_code == 200 and r.json()["aprovado"] is True and float(r.json()["nota"]) == 100.0
    async with AsyncSessionLocal() as db:
        tents = (await db.execute(select(TentativaQuiz).where(
            TentativaQuiz.matricula_id == mat_id, TentativaQuiz.quiz_id == ids["quiz_id"]))).scalars().all()
        assert len(tents) == 2 and sum(t.aprovado for t in tents) == 1
        aprovada = next(t for t in tents if t.aprovado)
        assert isinstance(aprovada.respostas, dict) and len(aprovada.respostas) == 2

    # ── 10. CERTIFICADO ──────────────────────────────────────────────────────
    r = await client.post(f"/api/v1/certificados/{mat_id}", headers=headers)
    assert r.status_code == 201, r.text
    codigo = r.json()["codigo_verificacao"]
    assert codigo.startswith("RC-")
    async with AsyncSessionLocal() as db:
        cdb = (await db.execute(select(Certificado).where(
            Certificado.matricula_id == mat_id))).scalar_one()
        assert cdb.codigo_verificacao == codigo
    # idempotência: 2ª emissão → 409
    r = await client.post(f"/api/v1/certificados/{mat_id}", headers=headers)
    assert r.status_code == 409

    # ── 11. VERIFICAÇÃO PÚBLICA ──────────────────────────────────────────────
    r = await client.get(f"/api/v1/certificados/{codigo}/verificar")
    assert r.status_code == 200
    v = r.json()
    assert v["valido"] is True and v["curso"] == "E2E Curso" and v["aluno_nome"] == "Aluno E2E"

    # ── 12. AVALIAÇÃO (upsert) ───────────────────────────────────────────────
    r = await client.post(f"/api/v1/cursos/{slug}/avaliacoes",
                          headers=headers, json={"nota": 5, "texto": "Excelente E2E"})
    assert r.status_code in (200, 201)
    async with AsyncSessionLocal() as db:
        av = (await db.execute(select(Avaliacao).where(
            Avaliacao.aluno_id == aluno_id, Avaliacao.curso_id == ids["curso_id"]))).scalar_one()
        assert av.nota == 5 and av.texto == "Excelente E2E"
    # reenvio = upsert (mesma linha, nota nova)
    await client.post(f"/api/v1/cursos/{slug}/avaliacoes",
                      headers=headers, json={"nota": 4, "texto": "Revisada"})
    async with AsyncSessionLocal() as db:
        n = await db.scalar(select(func.count(Avaliacao.id)).where(
            Avaliacao.aluno_id == aluno_id, Avaliacao.curso_id == ids["curso_id"]))
        av = (await db.execute(select(Avaliacao).where(
            Avaliacao.aluno_id == aluno_id, Avaliacao.curso_id == ids["curso_id"]))).scalar_one()
        assert n == 1 and av.nota == 4
