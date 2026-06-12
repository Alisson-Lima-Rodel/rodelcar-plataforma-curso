import uuid

import pytest
import pytest_asyncio
import stripe
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models import Admin, Aluno, Faq, PapelAdmin, Video

ADMIN_EMAIL = f"admin_{uuid.uuid4().hex[:8]}@rodelcar.dev"
ADMIN_PASS = "AdminTest123!"


@pytest.fixture(autouse=True)
def stripe_stub(monkeypatch):
    """Stub da SDK da Stripe p/ TODOS os testes do admin (sem chamadas reais).

    O container de teste tem STRIPE_SECRET_KEY no env, então `stripe_ativo()` é
    True e a sincronização roda — contra estes stubs. Retorna o registro de
    chamadas p/ os testes de sync inspecionarem.
    """
    chamadas: dict[str, list] = {
        "product_create": [], "price_create": [],
        "price_modify": [], "product_modify": [],
        "refund": [], "sub_cancel": [],
    }

    class _Stub:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    def product_create(**kw):
        chamadas["product_create"].append(kw)
        return _Stub(id=f"prod_stub_{len(chamadas['product_create'])}")

    def price_create(**kw):
        chamadas["price_create"].append(kw)
        return _Stub(id=f"price_stub_{uuid.uuid4().hex[:8]}")

    def price_retrieve(price_id, **kw):
        return {"id": price_id, "product": "prod_stub_ret"}

    def price_modify(price_id, **kw):
        chamadas["price_modify"].append((price_id, kw))
        return _Stub(id=price_id)

    def product_modify(product_id, **kw):
        chamadas["product_modify"].append((product_id, kw))
        return _Stub(id=product_id)

    def refund_create(**kw):
        chamadas["refund"].append(kw)
        return _Stub(id=f"re_stub_{len(chamadas['refund'])}")

    def sub_cancel(sub_id, **kw):
        chamadas["sub_cancel"].append(sub_id)
        return _Stub(id=sub_id, status="canceled")

    def invoice_payment_list(**kw):
        return {"data": [{"payment": {"type": "payment_intent", "payment_intent": "pi_da_invoice"}}]}

    monkeypatch.setattr(stripe.Product, "create", product_create)
    monkeypatch.setattr(stripe.Product, "modify", product_modify)
    monkeypatch.setattr(stripe.Price, "create", price_create)
    monkeypatch.setattr(stripe.Price, "retrieve", price_retrieve)
    monkeypatch.setattr(stripe.Price, "modify", price_modify)
    monkeypatch.setattr(stripe.Refund, "create", refund_create)
    monkeypatch.setattr(stripe.Subscription, "cancel", sub_cancel)
    monkeypatch.setattr(stripe.InvoicePayment, "list", invoice_payment_list)
    return chamadas


@pytest_asyncio.fixture
async def admin_user():
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args=settings.db_connect_args
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        admin = Admin(
            nome="Admin Teste",
            email=ADMIN_EMAIL,
            senha_hash=hash_password(ADMIN_PASS),
            papel=PapelAdmin.administrador,
            ativo=True,
        )
        s.add(admin)
        await s.commit()
        admin_id = admin.id
    yield {"id": str(admin_id), "email": ADMIN_EMAIL, "password": ADMIN_PASS}
    async with Session() as s:
        obj = await s.get(Admin, admin_id)
        if obj:
            await s.delete(obj)
            await s.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user: dict) -> dict:
    resp = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": admin_user["email"], "senha": admin_user["password"]},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Auth do painel ────────────────────────────────────────────────────────────
class TestAdminAuth:
    async def test_login_senha_errada_retorna_401(
        self, client: AsyncClient, admin_user: dict
    ):
        resp = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": admin_user["email"], "senha": "errada"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "CREDENCIAIS_INVALIDAS"

    async def test_login_ok_e_me(self, client: AsyncClient, admin_headers: dict):
        resp = await client.get("/api/v1/admin/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["papel"] == "Administrador"

    async def test_rota_admin_sem_token_retorna_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/videos")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "NAO_AUTENTICADO"

    async def test_token_de_aluno_nao_acessa_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Token de aluno (type=access) é rejeitado nas rotas de admin."""
        resp = await client.get("/api/v1/admin/videos", headers=auth_headers)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_INVALIDO"

    async def test_logout_invalida_token(self, client: AsyncClient, admin_user: dict):
        """Logout incrementa token_version → o access token deixa de valer."""
        login = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": admin_user["email"], "senha": admin_user["password"]},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert (await client.get("/api/v1/admin/auth/me", headers=headers)).status_code == 200
        assert (await client.post("/api/v1/admin/auth/logout", headers=headers)).status_code == 204
        # Mesmo token, agora com tv defasado → 401.
        resp = await client.get("/api/v1/admin/auth/me", headers=headers)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "TOKEN_INVALIDO"


# ── CRUD de Vídeos (fábrica _crud_router) ─────────────────────────────────────
class TestAdminVideos:
    async def test_ciclo_completo(self, client: AsyncClient, admin_headers: dict):
        # create
        resp = await client.post(
            "/api/v1/admin/videos",
            headers=admin_headers,
            json={"titulo": "Vídeo CRUD", "duracao": "05:00", "status": "Ativo"},
        )
        assert resp.status_code == 201
        vid = resp.json()
        assert vid["titulo"] == "Vídeo CRUD"
        vid_id = vid["id"]

        # list contém
        lista = (await client.get("/api/v1/admin/videos", headers=admin_headers)).json()
        assert any(v["id"] == vid_id for v in lista)

        # patch
        resp = await client.patch(
            f"/api/v1/admin/videos/{vid_id}",
            headers=admin_headers,
            json={"views": "9 mil"},
        )
        assert resp.status_code == 200
        assert resp.json()["views"] == "9 mil"

        # delete
        resp = await client.delete(
            f"/api/v1/admin/videos/{vid_id}", headers=admin_headers
        )
        assert resp.status_code == 204

        lista = (await client.get("/api/v1/admin/videos", headers=admin_headers)).json()
        assert not any(v["id"] == vid_id for v in lista)

    async def test_enriquece_do_youtube(
        self, client: AsyncClient, admin_headers: dict, monkeypatch
    ):
        """Só com a URL: título e canal são puxados do YouTube (oEmbed mockado)."""
        async def fake_meta(url):
            return {"titulo": "Como sangrar o câmbio DSG", "canal": "RödelCar"}

        monkeypatch.setattr("app.routers.admin.buscar_metadados", fake_meta)
        resp = await client.post(
            "/api/v1/admin/videos",
            headers=admin_headers,
            json={"youtube_url": "https://youtu.be/abc12345678", "estrelas": 4},
        )
        assert resp.status_code == 201
        v = resp.json()
        assert v["titulo"] == "Como sangrar o câmbio DSG"
        assert v["canal"] == "RödelCar"
        assert v["estrelas"] == 4
        await client.delete(f"/api/v1/admin/videos/{v['id']}", headers=admin_headers)

    async def test_titulo_manual_prevalece(
        self, client: AsyncClient, admin_headers: dict, monkeypatch
    ):
        """O que o admin digita não é sobrescrito pelo YouTube; canal em branco enche."""
        async def fake_meta(url):
            return {"titulo": "Título do YT", "canal": "Canal do YT"}

        monkeypatch.setattr("app.routers.admin.buscar_metadados", fake_meta)
        resp = await client.post(
            "/api/v1/admin/videos",
            headers=admin_headers,
            json={
                "youtube_url": "https://youtu.be/zzz99999999",
                "titulo": "Meu título custom",
            },
        )
        assert resp.status_code == 201
        v = resp.json()
        assert v["titulo"] == "Meu título custom"  # mantido
        assert v["canal"] == "Canal do YT"  # enriquecido
        assert v["estrelas"] == 5  # default
        await client.delete(f"/api/v1/admin/videos/{v['id']}", headers=admin_headers)


# ── CRUD de FAQ ───────────────────────────────────────────────────────────────
class TestAdminFaq:
    async def test_cria_e_exclui(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/admin/faqs",
            headers=admin_headers,
            json={"pergunta": "Pergunta CRUD?", "resposta": "Resposta CRUD."},
        )
        assert resp.status_code == 201
        faq_id = resp.json()["id"]
        assert resp.json()["status"] == "Ativo"

        resp = await client.delete(
            f"/api/v1/admin/faqs/{faq_id}", headers=admin_headers
        )
        assert resp.status_code == 204


# ── CRUD de Alunos (campos de matrícula derivados) ────────────────────────────
class TestAdminAlunos:
    async def test_cria_aluno_com_campos_derivados(
        self, client: AsyncClient, admin_headers: dict
    ):
        email = f"novo_{uuid.uuid4().hex[:8]}@rodelcar.dev"
        resp = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={
                "nome": "Aluno Novo",
                "email": email,
                "senha": "SenhaForte123",
                "telefone": "(51) 90000-0000",
            },
        )
        assert resp.status_code == 201
        aluno = resp.json()
        aluno_id = aluno["id"]
        # sem matrícula → derivados zerados
        assert aluno["matriculas"] == 0
        assert aluno["vigencia"] is None
        assert aluno["status"] == "Inativo"

        # email duplicado → 409
        dup = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={"nome": "Outro", "email": email, "senha": "SenhaForte123"},
        )
        assert dup.status_code == 409
        assert dup.json()["error"]["code"] == "EMAIL_EM_USO"

        # cleanup
        await client.delete(f"/api/v1/admin/alunos/{aluno_id}", headers=admin_headers)

    async def test_senha_curta_retorna_422(
        self, client: AsyncClient, admin_headers: dict
    ):
        resp = await client.post(
            "/api/v1/admin/alunos",
            headers=admin_headers,
            json={"nome": "X", "email": "x@y.dev", "senha": "123"},
        )
        assert resp.status_code == 422


# ── RBAC: papéis Editor/Suporte têm escopo restrito ───────────────────────────
@pytest_asyncio.fixture
async def suporte_headers(client: AsyncClient) -> dict:
    email = f"suporte_{uuid.uuid4().hex[:8]}@rodelcar.dev"
    senha = "SuporteTest123!"
    engine = create_async_engine(
        settings.DATABASE_URL, connect_args=settings.db_connect_args
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        adm = Admin(
            nome="Suporte Teste",
            email=email,
            senha_hash=hash_password(senha),
            papel=PapelAdmin.suporte,
            ativo=True,
        )
        s.add(adm)
        await s.commit()
        adm_id = adm.id
    resp = await client.post(
        "/api/v1/admin/auth/login", json={"email": email, "senha": senha}
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    yield headers
    async with Session() as s:
        obj = await s.get(Admin, adm_id)
        if obj:
            await s.delete(obj)
            await s.commit()
    await engine.dispose()


class TestAdminRBAC:
    async def test_suporte_bloqueado_em_cursos(
        self, client: AsyncClient, suporte_headers: dict
    ):
        resp = await client.get("/api/v1/admin/cursos", headers=suporte_headers)
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "PERMISSAO_NEGADA"

    async def test_suporte_bloqueado_em_administradores(
        self, client: AsyncClient, suporte_headers: dict
    ):
        resp = await client.get(
            "/api/v1/admin/administradores", headers=suporte_headers
        )
        assert resp.status_code == 403

    async def test_suporte_acessa_alunos(
        self, client: AsyncClient, suporte_headers: dict
    ):
        resp = await client.get("/api/v1/admin/alunos", headers=suporte_headers)
        assert resp.status_code == 200

    async def test_admin_nao_altera_proprio_papel(
        self, client: AsyncClient, admin_headers: dict, admin_user: dict
    ):
        resp = await client.patch(
            f"/api/v1/admin/administradores/{admin_user['id']}",
            headers=admin_headers,
            json={"papel": "Editor"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "AUTO_ALTERACAO_PAPEL"


# ── Planos de assinatura (Premium) ────────────────────────────────────────────
class TestAdminPlanos:
    async def test_ciclo_completo(self, client: AsyncClient, admin_headers: dict):
        pref = uuid.uuid4().hex[:8]
        # create
        resp = await client.post(
            "/api/v1/admin/planos",
            headers=admin_headers,
            json={
                "nome": f"Plano Teste {pref}",
                "intervalo": "anual",
                "stripe_price_id": f"price_adm_{pref}",
                "preco": 499.0,
            },
        )
        assert resp.status_code == 201
        plano = resp.json()
        assert plano["status"] == "Ativo"
        assert plano["stripe_price_id"] == f"price_adm_{pref}"

        # price duplicado → 409 (não 500)
        dup = await client.post(
            "/api/v1/admin/planos",
            headers=admin_headers,
            json={
                "nome": "Outro",
                "intervalo": "mensal",
                "stripe_price_id": f"price_adm_{pref}",
                "preco": 49.9,
            },
        )
        assert dup.status_code == 409
        assert dup.json()["error"]["code"] == "PRICE_EM_USO"

        # list
        lista = await client.get("/api/v1/admin/planos", headers=admin_headers)
        assert lista.status_code == 200
        assert any(p["id"] == plano["id"] for p in lista.json())

        # patch (desativa — some da vitrine pública)
        patch = await client.patch(
            f"/api/v1/admin/planos/{plano['id']}",
            headers=admin_headers,
            json={"status": "Inativo"},
        )
        assert patch.status_code == 200
        assert patch.json()["status"] == "Inativo"
        publico = await client.get("/api/v1/planos")
        assert plano["id"] not in [p["id"] for p in publico.json()]

        # delete
        dele = await client.delete(
            f"/api/v1/admin/planos/{plano['id']}", headers=admin_headers
        )
        assert dele.status_code == 204

    async def test_suporte_bloqueado_em_planos(
        self, client: AsyncClient, suporte_headers: dict
    ):
        resp = await client.get("/api/v1/admin/planos", headers=suporte_headers)
        assert resp.status_code == 403


# ── Sincronização admin → Stripe (Products/Prices) ────────────────────────────
class TestAdminStripeSync:
    async def test_criar_curso_cria_product_e_price(
        self, client: AsyncClient, admin_headers: dict, stripe_stub
    ):
        pref = uuid.uuid4().hex[:8]
        resp = await client.post(
            "/api/v1/admin/cursos",
            headers=admin_headers,
            json={"slug": f"sync-{pref}", "titulo": f"Curso Sync {pref}", "preco": 350},
        )
        assert resp.status_code == 201
        curso_id = resp.json()["id"]
        # Product + Price one-time criados na Stripe (350 → 35000 centavos).
        assert len(stripe_stub["product_create"]) == 1
        assert stripe_stub["price_create"][0]["unit_amount"] == 35000
        assert "recurring" not in stripe_stub["price_create"][0]

        # Editar o preço → Price NOVO + desativação do antigo.
        patch = await client.patch(
            f"/api/v1/admin/cursos/{curso_id}",
            headers=admin_headers,
            json={"preco": 399},
        )
        assert patch.status_code == 200
        assert stripe_stub["price_create"][-1]["unit_amount"] == 39900
        assert stripe_stub["price_modify"][-1][1] == {"active": False}

        # Renomear → Product.modify com o nome novo.
        patch2 = await client.patch(
            f"/api/v1/admin/cursos/{curso_id}",
            headers=admin_headers,
            json={"titulo": "Curso Sync Renomeado"},
        )
        assert patch2.status_code == 200
        assert stripe_stub["product_modify"][-1][1] == {"name": "Curso Sync Renomeado"}

        # Excluir → arquiva na Stripe (best-effort) e some do banco.
        dele = await client.delete(
            f"/api/v1/admin/cursos/{curso_id}", headers=admin_headers
        )
        assert dele.status_code == 204

    async def test_criar_plano_sem_price_cria_na_stripe(
        self, client: AsyncClient, admin_headers: dict, stripe_stub
    ):
        pref = uuid.uuid4().hex[:8]
        resp = await client.post(
            "/api/v1/admin/planos",
            headers=admin_headers,
            json={"nome": f"Plano Sync {pref}", "intervalo": "mensal", "preco": 59.9},
        )
        assert resp.status_code == 201
        plano = resp.json()
        assert plano["stripe_price_id"].startswith("price_stub_")
        assert stripe_stub["price_create"][-1]["recurring"] == {"interval": "month"}
        assert stripe_stub["price_create"][-1]["unit_amount"] == 5990

        # Mudar o preço → Price recorrente novo (mantém o intervalo) + desativa o antigo.
        patch = await client.patch(
            f"/api/v1/admin/planos/{plano['id']}",
            headers=admin_headers,
            json={"preco": 69.9},
        )
        assert patch.status_code == 200
        assert patch.json()["stripe_price_id"] != plano["stripe_price_id"]
        assert stripe_stub["price_create"][-1]["unit_amount"] == 6990
        assert stripe_stub["price_create"][-1]["recurring"] == {"interval": "month"}
        assert stripe_stub["price_modify"][-1][0] == plano["stripe_price_id"]

        dele = await client.delete(
            f"/api/v1/admin/planos/{patch.json()['id']}", headers=admin_headers
        )
        assert dele.status_code == 204

    async def test_patch_com_price_inalterado_ainda_sincroniza(
        self, client: AsyncClient, admin_headers: dict, stripe_stub
    ):
        """Regressão: o form do admin envia o objeto INTEIRO no PATCH (incluindo
        o stripe_price_id inalterado). Isso não é override manual — a troca de
        preço tem que sincronizar com a Stripe mesmo assim."""
        pref = uuid.uuid4().hex[:8]
        criado = await client.post(
            "/api/v1/admin/planos",
            headers=admin_headers,
            json={"nome": f"Plano Form {pref}", "intervalo": "anual", "preco": 499},
        )
        plano = criado.json()

        # PATCH como o form envia: todos os campos, price igual, preço novo.
        patch = await client.patch(
            f"/api/v1/admin/planos/{plano['id']}",
            headers=admin_headers,
            json={
                "nome": plano["nome"],
                "intervalo": plano["intervalo"],
                "stripe_price_id": plano["stripe_price_id"],  # inalterado
                "preco": 1499,
                "status": plano["status"],
                "ordem": plano["ordem"],
            },
        )
        assert patch.status_code == 200
        assert patch.json()["preco"] == 1499
        # Sincronizou: price novo de 149900 centavos e o antigo desativado.
        assert patch.json()["stripe_price_id"] != plano["stripe_price_id"]
        assert stripe_stub["price_create"][-1]["unit_amount"] == 149900
        assert stripe_stub["price_modify"][-1][0] == plano["stripe_price_id"]

        await client.delete(
            f"/api/v1/admin/planos/{plano['id']}", headers=admin_headers
        )

    async def test_criar_plano_sem_price_sem_stripe_400(
        self, client: AsyncClient, admin_headers: dict, monkeypatch
    ):
        monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
        resp = await client.post(
            "/api/v1/admin/planos",
            headers=admin_headers,
            json={"nome": "Plano Sem Stripe", "intervalo": "anual", "preco": 499},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "PRICE_OBRIGATORIO"


# ── Reembolsos pelo suporte (sem trava de 7 dias) ─────────────────────────────
@pytest_asyncio.fixture
async def reembolso_seed():
    """Aluno + curso + pagamento aprovado há 8 DIAS + matrícula ativa."""
    import datetime as dt
    from decimal import Decimal

    from app.core.db import AsyncSessionLocal
    from app.models import Curso, Matricula, Pagamento, StatusMatricula, StatusPagamento, TipoCurso

    pref = uuid.uuid4().hex[:8]
    email = f"reemb_{pref}@rodelcar.dev"
    async with AsyncSessionLocal() as db:
        aluno = Aluno(nome="Reembolso Tester", email=email, senha_hash=hash_password("x" * 8))
        db.add(aluno)
        await db.flush()
        curso = Curso(
            slug=f"reemb-{pref}", titulo="Curso Reembolso", tipo=TipoCurso.avulso,
            preco=Decimal("100.00"), validade_dias=365,
        )
        db.add(curso)
        await db.flush()
        pag = Pagamento(
            aluno_id=aluno.id, gateway="stripe", gateway_transaction_id=f"pi_{pref}_adm",
            valor=Decimal("100.00"), status=StatusPagamento.aprovado, payload={},
            criado_em=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=8),
        )
        db.add(pag)
        await db.flush()
        mat = Matricula(
            aluno_id=aluno.id, curso_id=curso.id, pagamento_id=pag.id,
            status=StatusMatricula.ativo,
            data_expiracao=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365),
        )
        db.add(mat)
        await db.flush()
        data = {
            "email": email, "aluno_id": str(aluno.id),
            "matricula_id": str(mat.id), "curso_id": str(curso.id),
            "pi": f"pi_{pref}_adm",
        }
        await db.commit()

    yield data

    from sqlalchemy import delete as _delete

    from app.core.db import AsyncSessionLocal as _S
    from app.models import Curso as _C, Matricula as _M, Pagamento as _P

    aid = uuid.UUID(data["aluno_id"])
    async with _S() as db:
        await db.execute(_delete(_M).where(_M.aluno_id == aid))
        await db.execute(_delete(_P).where(_P.aluno_id == aid))
        await db.execute(_delete(_C).where(_C.id == uuid.UUID(data["curso_id"])))
        await db.execute(_delete(Aluno).where(Aluno.id == aid))
        await db.commit()


class TestAdminReembolsos:
    async def test_busca_e_cancela_fora_da_janela(
        self, client: AsyncClient, admin_headers: dict, reembolso_seed, stripe_stub
    ):
        # Busca por e-mail: matrícula cancelável, mas FORA da janela de 7 dias.
        busca = await client.get(
            f"/api/v1/admin/reembolsos?email={reembolso_seed['email']}",
            headers=admin_headers,
        )
        assert busca.status_code == 200
        body = busca.json()
        assert body["email"] == reembolso_seed["email"]
        item = body["matriculas"][0]
        assert item["cancelavel"] is True
        assert item["dentro_da_janela"] is False  # 8 dias — aluno não pode, admin pode

        # Admin cancela mesmo fora da janela (cortesia) → reembolso + expira.
        resp = await client.post(
            f"/api/v1/admin/reembolsos/{reembolso_seed['matricula_id']}/cancelar",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["reembolsado"] is True
        assert stripe_stub["refund"][-1]["payment_intent"] == reembolso_seed["pi"]

    async def test_aluno_inexistente_404(self, client: AsyncClient, admin_headers: dict):
        resp = await client.get(
            "/api/v1/admin/reembolsos?email=naoexiste@rodelcar.dev",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    async def test_suporte_pode_reembolsar(
        self, client: AsyncClient, suporte_headers: dict, reembolso_seed
    ):
        resp = await client.get(
            f"/api/v1/admin/reembolsos?email={reembolso_seed['email']}",
            headers=suporte_headers,
        )
        assert resp.status_code == 200
