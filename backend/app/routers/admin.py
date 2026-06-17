import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from pydantic import EmailStr
from sqlalchemy import case, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.db import get_db
from app.core.ratelimit import auth_limit, limiter
from app.core.security import create_admin_token, dummy_verify, hash_password, verify_password
from app.core.stripe_admin import (
    arquivar_price,
    criar_price_curso,
    criar_price_plano,
    renomear_produto,
    stripe_ativo,
    trocar_preco,
)
from app.core.storage import MAX_BYTES, StorageError, storage_ativo, upload_imagem
from app.core.stripe_refunds import executar_cancelamento, limite_cancelamento
from app.core.youtube import buscar_metadados
from app.dependencies import get_current_admin, require_papel
from app.core.stripe_coupons import (
    arquivar_cupom_stripe,
    criar_cupom_stripe,
    set_cupom_ativo,
)
from app.models import (
    Admin,
    Alternativa,
    Aluno,
    Aula,
    Avaliacao,
    Cupom,
    Curso,
    Depoimento,
    Faq,
    MaterialApoio,
    Matricula,
    Modulo,
    Pagamento,
    PapelAdmin,
    PlanoAssinatura,
    Progresso,
    Questao,
    Quiz,
    StatusMatricula,
    StatusPagamento,
    TentativaQuiz,
    TipoCurso,
    Video,
)
from app.schemas.me import CancelamentoResultado
from app.schemas.quizzes import (
    AlternativaAdminOut,
    QuestaoAdminOut,
    QuizAdmin,
    QuizUpsert,
)

# Escopos de papel (RBAC). Administrador faz tudo; Editor cuida de conteúdo
# (cursos/planos/depoimentos/vídeos/FAQ); Suporte cuida de alunos.
_CONTEUDO = (PapelAdmin.administrador, PapelAdmin.editor)
_ALUNOS = (PapelAdmin.administrador, PapelAdmin.suporte)
_SO_ADMIN = (PapelAdmin.administrador,)
from app.schemas.admin import (
    AdminLoginRequest,
    AdminMe,
    AdminTokenResponse,
    AdminUserCreate,
    AdminUserItem,
    AdminUserUpdate,
    AlunoAdminItem,
    AlunoCreate,
    AlunoUpdate,
    CursoAdmin,
    CursoCreate,
    CursoUpdate,
    DepoimentoAdmin,
    DepoimentoCreate,
    DepoimentoUpdate,
    FaqAdmin,
    FaqCreate,
    FaqUpdate,
    AlunoReembolsos,
    AvaliacaoAdminItem,
    AvaliacaoStatusUpdate,
    CupomAdmin,
    CupomCreate,
    CupomUpdate,
    PlanoAssinaturaAdmin,
    PlanoAssinaturaCreate,
    PlanoAssinaturaUpdate,
    ReembolsoItem,
    VideoAdmin,
    VideoCreate,
    VideoUpdate,
)
from app.core import panda
from app.schemas.conteudo_admin import (
    AulaAdmin,
    AulaCreate,
    AulaSyncResponse,
    AulaUpdate,
    AulaUploadRequest,
    AulaUploadResponse,
    ModuloAdmin,
    ModuloCreate,
    ModuloUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


# ── Auth ──────────────────────────────────────────────────────────────────────
@router.post("/auth/login", response_model=AdminTokenResponse)
@limiter.limit(auth_limit)
async def admin_login(request: Request, body: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    admin = (await db.execute(select(Admin).where(Admin.email == body.email))).scalar_one_or_none()
    # Equaliza o tempo quando o e-mail não existe (anti-enumeração por timing).
    if admin is None:
        dummy_verify()
        raise _err(401, "CREDENCIAIS_INVALIDAS", "E-mail ou senha incorretos.")
    if not admin.ativo or not verify_password(body.senha, admin.senha_hash):
        raise _err(401, "CREDENCIAIS_INVALIDAS", "E-mail ou senha incorretos.")
    admin.ultimo_acesso = datetime.now(timezone.utc)
    await db.commit()
    return AdminTokenResponse(
        access_token=create_admin_token(str(admin.id), admin.token_version),
        expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
    )


@router.get("/auth/me", response_model=AdminMe)
async def admin_me(admin: Admin = Depends(get_current_admin)):
    return admin


@router.post("/auth/logout", status_code=204)
async def admin_logout(
    admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    """Logout do painel: incrementa token_version e invalida os access tokens vivos
    deste admin (o admin não usa refresh; esta é a forma de revogar a sessão)."""
    admin.token_version += 1
    await db.commit()
    return Response(status_code=204)


# ── Cursos (CRUD) — protegido por admin ───────────────────────────────────────
cursos = APIRouter(prefix="/cursos", dependencies=[Depends(require_papel(*_CONTEUDO))])


@cursos.get("", response_model=list[CursoAdmin])
async def listar_cursos(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Curso).order_by(Curso.ordem, Curso.titulo))).scalars().all()


@cursos.post("", response_model=CursoAdmin, status_code=201)
async def criar_curso(body: CursoCreate, db: AsyncSession = Depends(get_db)):
    if await db.scalar(select(Curso.id).where(Curso.slug == body.slug)):
        raise _err(409, "SLUG_EM_USO", "Já existe um curso com esse slug.")
    curso = Curso(**body.model_dump(), aprende=[])
    # Sincroniza com a Stripe: curso avulso nasce vendável (Product+Price).
    if curso.tipo == TipoCurso.avulso and stripe_ativo():
        try:
            curso.stripe_price_id = await criar_price_curso(
                curso.titulo, curso.slug, float(curso.preco or 0)
            )
        except stripe.error.StripeError:
            raise _err(502, "STRIPE_ERRO", "Falha ao criar o produto na Stripe — curso não salvo.")
    db.add(curso)
    await db.commit()
    await db.refresh(curso)
    return curso


@cursos.patch("/{curso_id}", response_model=CursoAdmin)
async def atualizar_curso(
    curso_id: uuid.UUID,
    body: CursoUpdate,
    atual: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    curso = await db.get(Curso, curso_id)
    if curso is None:
        raise _err(404, "CURSO_NAO_ENCONTRADO", "Curso não encontrado.")
    data = body.model_dump(exclude_unset=True)
    # Marcar/desmarcar um curso como GRATUITO afeta receita → só Administrador.
    if (
        "gratuito" in data
        and data["gratuito"] != curso.gratuito
        and atual.papel != PapelAdmin.administrador
    ):
        raise _err(
            403, "SO_ADMIN_GRATUITO",
            "Só um Administrador pode marcar/desmarcar um curso como gratuito.",
        )
    if "slug" in data and data["slug"] != curso.slug:
        if await db.scalar(select(Curso.id).where(Curso.slug == data["slug"])):
            raise _err(409, "SLUG_EM_USO", "Já existe um curso com esse slug.")

    # Sincroniza com a Stripe ANTES do commit (falhou lá → nada muda aqui).
    muda_preco = "preco" in data and float(data["preco"] or 0) != float(curso.preco or 0)
    muda_titulo = "titulo" in data and data["titulo"] != curso.titulo
    if stripe_ativo():
        try:
            if curso.stripe_price_id:
                if muda_preco:
                    data["stripe_price_id"] = await trocar_preco(
                        curso.stripe_price_id, float(data["preco"])
                    )
                if muda_titulo:
                    await renomear_produto(curso.stripe_price_id, data["titulo"])
            elif muda_preco and curso.tipo == TipoCurso.avulso:
                # Curso ainda sem produto na Stripe: cria na 1ª edição de preço.
                data["stripe_price_id"] = await criar_price_curso(
                    data.get("titulo", curso.titulo), curso.slug, float(data["preco"])
                )
        except stripe.error.StripeError:
            raise _err(502, "STRIPE_ERRO", "Falha ao sincronizar com a Stripe — alteração não aplicada.")

    for k, v in data.items():
        setattr(curso, k, v)
    await db.commit()
    await db.refresh(curso)
    return curso


@cursos.delete("/{curso_id}", status_code=204)
async def excluir_curso(curso_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    curso = await db.get(Curso, curso_id)
    if curso is None:
        raise _err(404, "CURSO_NAO_ENCONTRADO", "Curso não encontrado.")
    if await db.scalar(select(Matricula.id).where(Matricula.curso_id == curso_id)):
        raise _err(409, "CURSO_COM_MATRICULA", "Há alunos matriculados — não é possível excluir.")
    mod_ids = (await db.execute(select(Modulo.id).where(Modulo.curso_id == curso_id))).scalars().all()
    if mod_ids:
        await db.execute(delete(Aula).where(Aula.modulo_id.in_(mod_ids)))
        await db.execute(delete(Modulo).where(Modulo.curso_id == curso_id))
    if curso.stripe_price_id and stripe_ativo():
        await arquivar_price(curso.stripe_price_id)  # best-effort (não bloqueia)
    await db.delete(curso)
    await db.commit()
    return Response(status_code=204)


router.include_router(cursos)


# ── Alunos (gestão) — cursos/vigência/status são derivados de matrícula ───────
alunos = APIRouter(prefix="/alunos", dependencies=[Depends(require_papel(*_ALUNOS))])


async def _alunos_agg(db: AsyncSession) -> dict:
    """Por aluno: (nº de matrículas, maior data_expiracao, tem matrícula ativa?)."""
    rows = (
        await db.execute(
            select(
                Matricula.aluno_id,
                func.count(Matricula.id),
                func.max(Matricula.data_expiracao),
                func.max(case((Matricula.status == StatusMatricula.ativo, 1), else_=0)),
            ).group_by(Matricula.aluno_id)
        )
    ).all()
    return {r[0]: (r[1], r[2], bool(r[3])) for r in rows}


def _aluno_item(a: Aluno, agg: tuple) -> AlunoAdminItem:
    count, vig, ativo = agg
    return AlunoAdminItem(
        id=a.id,
        nome=a.nome,
        email=a.email,
        telefone=a.telefone,
        matriculas=count,
        vigencia=vig.date() if vig else None,
        status="Ativo" if ativo else "Inativo",
    )


@alunos.get("", response_model=list[AlunoAdminItem])
async def listar_alunos(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Aluno).order_by(Aluno.criado_em.desc()))).scalars().all()
    agg = await _alunos_agg(db)
    return [_aluno_item(a, agg.get(a.id, (0, None, False))) for a in rows]


@alunos.post("", response_model=AlunoAdminItem, status_code=201)
async def criar_aluno(body: AlunoCreate, db: AsyncSession = Depends(get_db)):
    if await db.scalar(select(Aluno.id).where(Aluno.email == body.email)):
        raise _err(409, "EMAIL_EM_USO", "Já existe um aluno com esse e-mail.")
    obj = Aluno(
        nome=body.nome,
        email=body.email,
        telefone=body.telefone,
        senha_hash=hash_password(body.senha),
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return _aluno_item(obj, (0, None, False))


@alunos.patch("/{aluno_id}", response_model=AlunoAdminItem)
async def atualizar_aluno(aluno_id: uuid.UUID, body: AlunoUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Aluno, aluno_id)
    if obj is None:
        raise _err(404, "NAO_ENCONTRADO", "Aluno não encontrado.")
    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != obj.email:
        if await db.scalar(select(Aluno.id).where(Aluno.email == data["email"])):
            raise _err(409, "EMAIL_EM_USO", "E-mail já em uso.")
    if "senha" in data:
        senha = data.pop("senha")
        if senha:
            obj.senha_hash = hash_password(senha)
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    agg = await _alunos_agg(db)
    return _aluno_item(obj, agg.get(obj.id, (0, None, False)))


@alunos.delete("/{aluno_id}", status_code=204)
async def excluir_aluno(aluno_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Aluno, aluno_id)
    if obj is None:
        raise _err(404, "NAO_ENCONTRADO", "Aluno não encontrado.")
    if await db.scalar(select(Matricula.id).where(Matricula.aluno_id == aluno_id)):
        raise _err(409, "ALUNO_COM_MATRICULA", "Aluno possui matrículas — não é possível excluir.")
    await db.delete(obj)
    await db.commit()
    return Response(status_code=204)


router.include_router(alunos)


# ── CRUD genérico p/ cadastros simples (Depoimentos, Vídeos, FAQ) ─────────────
def _crud_router(prefix, model, read_schema, create_schema, update_schema, papeis=_CONTEUDO, enrich=None):
    r = APIRouter(prefix=prefix, dependencies=[Depends(require_papel(*papeis))])

    @r.get("", response_model=list[read_schema])
    async def listar(db: AsyncSession = Depends(get_db)):
        return (await db.execute(select(model).order_by(model.ordem, model.criado_em))).scalars().all()

    @r.post("", response_model=read_schema, status_code=201)
    async def criar(body: create_schema, db: AsyncSession = Depends(get_db)):  # type: ignore[valid-type]
        data = body.model_dump()
        if enrich is not None:
            data = await enrich(data)
        obj = model(**data)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    @r.patch("/{obj_id}", response_model=read_schema)
    async def atualizar(obj_id: uuid.UUID, body: update_schema, db: AsyncSession = Depends(get_db)):  # type: ignore[valid-type]
        obj = await db.get(model, obj_id)
        if obj is None:
            raise _err(404, "NAO_ENCONTRADO", "Registro não encontrado.")
        data = body.model_dump(exclude_unset=True)
        # O form do admin envia o objeto inteiro: re-salvar com a URL repuxa o
        # que estiver em branco (ex.: canal de um vídeo antigo). enrich só enche
        # vazios — o que o admin digitou não é tocado.
        if enrich is not None:
            data = await enrich(data)
        for k, v in data.items():
            setattr(obj, k, v)
        await db.commit()
        await db.refresh(obj)
        return obj

    @r.delete("/{obj_id}", status_code=204)
    async def excluir(obj_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
        obj = await db.get(model, obj_id)
        if obj is None:
            raise _err(404, "NAO_ENCONTRADO", "Registro não encontrado.")
        await db.delete(obj)
        await db.commit()
        return Response(status_code=204)

    return r


_VIDEO_LIMITES = {"titulo": 200, "canal": 120, "duracao": 20, "views": 40, "likes": 40}


async def _enriquecer_video(data: dict) -> dict:
    """No cadastro, completa do YouTube o que veio em branco — o que o admin
    digitou prevalece. Com YOUTUBE_API_KEY: título, canal, duração, views e likes;
    sem a chave: só título e canal (oEmbed)."""
    if not data.get("youtube_url"):
        return data
    meta = await buscar_metadados(data["youtube_url"])
    if meta:
        for campo, limite in _VIDEO_LIMITES.items():
            valor = meta.get(campo)
            if valor and not (data.get(campo) or "").strip():
                data[campo] = str(valor)[:limite]
    if not (data.get("titulo") or "").strip():
        data["titulo"] = (data.get("canal") or "Vídeo do YouTube")[:200]
    return data


router.include_router(_crud_router("/depoimentos", Depoimento, DepoimentoAdmin, DepoimentoCreate, DepoimentoUpdate))
router.include_router(_crud_router(
    "/videos", Video, VideoAdmin, VideoCreate, VideoUpdate, enrich=_enriquecer_video
))
router.include_router(_crud_router("/faqs", Faq, FaqAdmin, FaqCreate, FaqUpdate))


# ── Planos de assinatura (Premium) — fora do CRUD genérico pela checagem de ──
# duplicidade do stripe_price_id (unique no banco; sem isso, 500 em vez de 409).
planos = APIRouter(prefix="/planos", dependencies=[Depends(require_papel(*_CONTEUDO))])


@planos.get("", response_model=list[PlanoAssinaturaAdmin])
async def listar_planos_admin(db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(
            select(PlanoAssinatura).order_by(PlanoAssinatura.ordem, PlanoAssinatura.criado_em)
        )
    ).scalars().all()


@planos.post("", response_model=PlanoAssinaturaAdmin, status_code=201)
async def criar_plano(body: PlanoAssinaturaCreate, db: AsyncSession = Depends(get_db)):
    data = body.model_dump()
    if not data.get("stripe_price_id"):
        # Sem price informado → cria Product + Price recorrente na Stripe.
        if not stripe_ativo():
            raise _err(
                400, "PRICE_OBRIGATORIO",
                "Sem Stripe configurado: informe um Stripe Price ID existente.",
            )
        try:
            data["stripe_price_id"] = await criar_price_plano(
                data["nome"], data["intervalo"], float(data["preco"] or 0)
            )
        except stripe.error.StripeError:
            raise _err(502, "STRIPE_ERRO", "Falha ao criar o plano na Stripe — nada salvo.")
    elif await db.scalar(
        select(PlanoAssinatura.id).where(PlanoAssinatura.stripe_price_id == data["stripe_price_id"])
    ):
        raise _err(409, "PRICE_EM_USO", "Já existe um plano com esse Stripe Price ID.")
    obj = PlanoAssinatura(**data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@planos.patch("/{plano_id}", response_model=PlanoAssinaturaAdmin)
async def atualizar_plano(
    plano_id: uuid.UUID, body: PlanoAssinaturaUpdate, db: AsyncSession = Depends(get_db)
):
    obj = await db.get(PlanoAssinatura, plano_id)
    if obj is None:
        raise _err(404, "NAO_ENCONTRADO", "Plano não encontrado.")
    # O schema de update NÃO aceita stripe_price_id (chave extra do form é
    # ignorada pelo Pydantic) — o id é gerido somente pela sincronização abaixo.
    data = body.model_dump(exclude_unset=True)

    # Preço/intervalo novo → Price novo p/ as PRÓXIMAS vendas; assinaturas
    # existentes mantêm o valor contratado (padrão Stripe).
    muda_preco = "preco" in data and float(data["preco"] or 0) != float(obj.preco or 0)
    muda_intervalo = "intervalo" in data and data["intervalo"] != obj.intervalo
    muda_nome = "nome" in data and data["nome"] != obj.nome
    if stripe_ativo() and obj.stripe_price_id:
        try:
            if muda_preco or muda_intervalo:
                data["stripe_price_id"] = await trocar_preco(
                    obj.stripe_price_id,
                    float(data.get("preco", obj.preco)),
                    data.get("intervalo", obj.intervalo),
                )
            if muda_nome:
                await renomear_produto(obj.stripe_price_id, data["nome"])
        except stripe.error.StripeError:
            raise _err(502, "STRIPE_ERRO", "Falha ao sincronizar com a Stripe — alteração não aplicada.")

    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@planos.delete("/{plano_id}", status_code=204)
async def excluir_plano(plano_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await db.get(PlanoAssinatura, plano_id)
    if obj is None:
        raise _err(404, "NAO_ENCONTRADO", "Plano não encontrado.")
    # Assinaturas já vendidas não dependem do plano (a renovação segue o
    # stripe_subscription_id da matrícula) — excluir só tira o plano da vitrine.
    if obj.stripe_price_id and stripe_ativo():
        await arquivar_price(obj.stripe_price_id)  # best-effort (não bloqueia)
    await db.delete(obj)
    await db.commit()
    return Response(status_code=204)


router.include_router(planos)


# ── Conteúdo do curso (módulos e aulas) ───────────────────────────────────────
conteudo = APIRouter(dependencies=[Depends(require_papel(*_CONTEUDO))])


def _aula_admin(a: Aula) -> AulaAdmin:
    return AulaAdmin(
        id=a.id, titulo=a.titulo, panda_video_id=a.panda_video_id,
        duracao_segundos=a.duracao_segundos, ordem=a.ordem, gratuita=a.gratuita,
    )


def _modulo_admin(m: Modulo, aulas: list[Aula]) -> ModuloAdmin:
    return ModuloAdmin(
        id=m.id, titulo=m.titulo, ordem=m.ordem,
        aulas=[_aula_admin(a) for a in sorted(aulas, key=lambda x: x.ordem)],
    )


async def _aulas_do_modulo(db: AsyncSession, modulo_id: uuid.UUID) -> list[Aula]:
    return list(
        (
            await db.execute(
                select(Aula).where(Aula.modulo_id == modulo_id).order_by(Aula.ordem)
            )
        ).scalars().all()
    )


async def _tem_progresso(db: AsyncSession, aula_ids: list[uuid.UUID]) -> bool:
    """Algum aluno já registrou progresso nestas aulas? Trava destrutiva: excluir
    aula/módulo apagaria irreversivelmente o histórico do aluno (espelha a trava de
    matrícula em excluir_curso)."""
    if not aula_ids:
        return False
    return bool(
        await db.scalar(
            select(Progresso.id).where(Progresso.aula_id.in_(aula_ids)).limit(1)
        )
    )


async def _excluir_aulas(db: AsyncSession, aula_ids: list[uuid.UUID]) -> None:
    """Remove aulas e o que pende delas (materiais, progresso). Só é chamada após
    a trava _tem_progresso — então Progresso aqui está vazio (defesa em profundidade)."""
    if not aula_ids:
        return
    await db.execute(delete(Progresso).where(Progresso.aula_id.in_(aula_ids)))
    await db.execute(delete(MaterialApoio).where(MaterialApoio.aula_id.in_(aula_ids)))
    await db.execute(delete(Aula).where(Aula.id.in_(aula_ids)))


@conteudo.get("/cursos/{curso_id}/conteudo", response_model=list[ModuloAdmin])
async def listar_conteudo(curso_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    if not await db.get(Curso, curso_id):
        raise _err(404, "CURSO_NAO_ENCONTRADO", "Curso não encontrado.")
    modulos = (
        await db.execute(
            select(Modulo)
            .where(Modulo.curso_id == curso_id)
            .options(selectinload(Modulo.aulas))
            .order_by(Modulo.ordem)
        )
    ).scalars().all()
    return [_modulo_admin(m, m.aulas) for m in modulos]


@conteudo.post("/cursos/{curso_id}/modulos", response_model=ModuloAdmin, status_code=201)
async def criar_modulo(
    curso_id: uuid.UUID, body: ModuloCreate, db: AsyncSession = Depends(get_db)
):
    if not await db.get(Curso, curso_id):
        raise _err(404, "CURSO_NAO_ENCONTRADO", "Curso não encontrado.")
    m = Modulo(curso_id=curso_id, titulo=body.titulo, ordem=body.ordem)
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return _modulo_admin(m, [])


@conteudo.patch("/modulos/{modulo_id}", response_model=ModuloAdmin)
async def atualizar_modulo(
    modulo_id: uuid.UUID, body: ModuloUpdate, db: AsyncSession = Depends(get_db)
):
    m = await db.get(Modulo, modulo_id)
    if m is None:
        raise _err(404, "NAO_ENCONTRADO", "Módulo não encontrado.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    await db.commit()
    return _modulo_admin(m, await _aulas_do_modulo(db, modulo_id))


@conteudo.delete("/modulos/{modulo_id}", status_code=204)
async def excluir_modulo(modulo_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    m = await db.get(Modulo, modulo_id)
    if m is None:
        raise _err(404, "NAO_ENCONTRADO", "Módulo não encontrado.")
    aulas = await _aulas_do_modulo(db, modulo_id)
    aula_ids = [a.id for a in aulas]
    if await _tem_progresso(db, aula_ids):
        raise _err(
            409, "MODULO_COM_PROGRESSO",
            "Há alunos com progresso em aulas deste módulo — não é possível excluir.",
        )
    await _excluir_aulas(db, aula_ids)
    await db.delete(m)
    await db.commit()
    return Response(status_code=204)


@conteudo.post("/modulos/{modulo_id}/aulas", response_model=AulaAdmin, status_code=201)
async def criar_aula(
    modulo_id: uuid.UUID, body: AulaCreate, db: AsyncSession = Depends(get_db)
):
    if not await db.get(Modulo, modulo_id):
        raise _err(404, "NAO_ENCONTRADO", "Módulo não encontrado.")
    a = Aula(modulo_id=modulo_id, **body.model_dump())
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return _aula_admin(a)


@conteudo.patch("/aulas/{aula_id}", response_model=AulaAdmin)
async def atualizar_aula(
    aula_id: uuid.UUID, body: AulaUpdate, db: AsyncSession = Depends(get_db)
):
    a = await db.get(Aula, aula_id)
    if a is None:
        raise _err(404, "NAO_ENCONTRADO", "Aula não encontrada.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    await db.commit()
    await db.refresh(a)
    return _aula_admin(a)


@conteudo.post("/aulas/{aula_id}/upload-url", response_model=AulaUploadResponse)
async def gerar_upload_aula(
    aula_id: uuid.UUID, body: AulaUploadRequest, db: AsyncSession = Depends(get_db)
):
    """Cria a sessão de upload no Panda (mediado) e grava o video_id na aula.

    O browser sobe o arquivo direto para `upload_url` (PATCH TUS) — a PANDA_API_KEY
    nunca sai do backend. Depois da conversão, chame /sync-panda para a duração."""
    a = await db.get(Aula, aula_id)
    if a is None:
        raise _err(404, "NAO_ENCONTRADO", "Aula não encontrada.")
    if not settings.panda_ativo:
        raise _err(
            503, "PANDA_INDISPONIVEL",
            "Upload de vídeo indisponível (PANDA_API_KEY não configurada).",
        )
    try:
        res = await panda.criar_upload(filename=body.filename, size=body.size)
    except panda.PandaIndisponivel as exc:
        raise _err(502, "PANDA_ERRO", str(exc))
    a.panda_video_id = res["video_id"]
    await db.commit()
    return AulaUploadResponse(video_id=res["video_id"], upload_url=res["upload_url"])


@conteudo.post("/aulas/{aula_id}/sync-panda", response_model=AulaSyncResponse)
async def sincronizar_aula_panda(
    aula_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Puxa duração/capa/status do Panda e preenche `duracao_segundos` da aula."""
    a = await db.get(Aula, aula_id)
    if a is None:
        raise _err(404, "NAO_ENCONTRADO", "Aula não encontrada.")
    if not a.panda_video_id:
        raise _err(409, "SEM_VIDEO", "Aula sem vídeo do Panda para sincronizar.")
    if not settings.panda_ativo:
        raise _err(
            503, "PANDA_INDISPONIVEL",
            "Sincronização indisponível (PANDA_API_KEY não configurada).",
        )
    try:
        video = await panda.obter_video(a.panda_video_id)
    except panda.PandaIndisponivel as exc:
        raise _err(502, "PANDA_ERRO", str(exc))
    dur = panda.duracao_segundos(video)
    if dur is not None and dur != a.duracao_segundos:
        a.duracao_segundos = dur
        await db.commit()
    return AulaSyncResponse(
        panda_video_id=a.panda_video_id,
        status=video.get("status"),
        duracao_segundos=a.duracao_segundos,
        thumbnail=panda.thumbnail_url(video),
    )


@conteudo.delete("/aulas/{aula_id}", status_code=204)
async def excluir_aula(aula_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    a = await db.get(Aula, aula_id)
    if a is None:
        raise _err(404, "NAO_ENCONTRADO", "Aula não encontrada.")
    if await _tem_progresso(db, [aula_id]):
        raise _err(
            409, "AULA_COM_PROGRESSO",
            "Há alunos com progresso nesta aula — não é possível excluir.",
        )
    await _excluir_aulas(db, [aula_id])
    await db.commit()
    return Response(status_code=204)


# ── Quiz do módulo (com gabarito) ─────────────────────────────────────────────
def _quiz_admin(quiz: Quiz) -> QuizAdmin:
    return QuizAdmin(
        id=quiz.id,
        modulo_id=quiz.modulo_id,
        titulo=quiz.titulo,
        nota_corte=float(quiz.nota_corte),
        ativo=quiz.ativo,
        questoes=[
            QuestaoAdminOut(
                id=q.id,
                enunciado=q.enunciado,
                alternativas=[
                    AlternativaAdminOut(id=a.id, texto=a.texto, correta=a.correta)
                    for a in q.alternativas
                ],
            )
            for q in quiz.questoes
        ],
    )


async def _carregar_quiz(db: AsyncSession, modulo_id: uuid.UUID) -> Quiz | None:
    return (
        await db.execute(
            select(Quiz)
            .where(Quiz.modulo_id == modulo_id)
            .options(selectinload(Quiz.questoes).selectinload(Questao.alternativas))
        )
    ).scalar_one_or_none()


@conteudo.get("/modulos/{modulo_id}/quiz", response_model=QuizAdmin | None)
async def obter_quiz_admin(modulo_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    quiz = await _carregar_quiz(db, modulo_id)
    return _quiz_admin(quiz) if quiz else None


@conteudo.put("/modulos/{modulo_id}/quiz", response_model=QuizAdmin)
async def upsert_quiz(
    modulo_id: uuid.UUID, body: QuizUpsert, db: AsyncSession = Depends(get_db)
):
    """Cria ou substitui (full replace das questões) o quiz do módulo. Preserva o
    id do quiz (e as tentativas dos alunos) — só troca o conjunto de questões."""
    if not await db.get(Modulo, modulo_id):
        raise _err(404, "NAO_ENCONTRADO", "Módulo não encontrado.")
    for q in body.questoes:
        if sum(1 for a in q.alternativas if a.correta) != 1:
            raise _err(
                422, "QUESTAO_SEM_GABARITO",
                "Cada questão precisa de exatamente UMA alternativa correta.",
            )

    quiz = await _carregar_quiz(db, modulo_id)
    if quiz is None:
        quiz = Quiz(
            modulo_id=modulo_id, titulo=body.titulo,
            nota_corte=body.nota_corte, ativo=body.ativo,
        )
        db.add(quiz)
        try:
            await db.flush()  # uq_quiz_modulo: corrida de 2 admins criando o mesmo
        except IntegrityError:
            await db.rollback()
            raise _err(409, "QUIZ_JA_EXISTE", "Este módulo já tem um quiz.")
    else:
        quiz.titulo = body.titulo
        quiz.nota_corte = body.nota_corte
        quiz.ativo = body.ativo
        await db.execute(delete(Questao).where(Questao.quiz_id == quiz.id))
        await db.flush()
    for i, q in enumerate(body.questoes):
        questao = Questao(quiz_id=quiz.id, enunciado=q.enunciado, ordem=i)
        db.add(questao)
        await db.flush()
        for j, a in enumerate(q.alternativas):
            db.add(Alternativa(
                questao_id=questao.id, texto=a.texto, correta=a.correta, ordem=j
            ))
    await db.commit()
    return _quiz_admin(await _carregar_quiz(db, modulo_id))


@conteudo.delete("/modulos/{modulo_id}/quiz", status_code=204)
async def excluir_quiz(modulo_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    quiz = await db.scalar(select(Quiz).where(Quiz.modulo_id == modulo_id))
    if quiz is not None:
        # Trava defensiva (igual a excluir_aula/excluir_modulo): excluir o quiz
        # CASCATEIA as tentativas dos alunos — apagaria provas já aprovadas e
        # poderia rebloquear certificados. Se há histórico, exija desativar.
        tem_tentativa = await db.scalar(
            select(TentativaQuiz.id).where(TentativaQuiz.quiz_id == quiz.id).limit(1)
        )
        if tem_tentativa is not None:
            raise _err(
                409, "QUIZ_COM_TENTATIVAS",
                "Há alunos com tentativas neste quiz — desative-o em vez de excluir.",
            )
        await db.delete(quiz)  # cascateia questões/alternativas
        await db.commit()
    return Response(status_code=204)


router.include_router(conteudo)


# ── Avaliações dos alunos (moderação) ─────────────────────────────────────────
avaliacoes = APIRouter(prefix="/avaliacoes", dependencies=[Depends(require_papel(*_CONTEUDO))])


@avaliacoes.get("", response_model=list[AvaliacaoAdminItem])
async def listar_avaliacoes_admin(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Avaliacao, Aluno.nome, Curso.titulo)
            .join(Aluno, Avaliacao.aluno_id == Aluno.id)
            .join(Curso, Avaliacao.curso_id == Curso.id)
            .order_by(Avaliacao.criado_em.desc())
        )
    ).all()
    return [
        AvaliacaoAdminItem(
            id=a.id,
            aluno_nome=nome,
            curso_titulo=titulo,
            nota=a.nota,
            texto=a.texto,
            status=a.status,
            criado_em=a.criado_em,
        )
        for a, nome, titulo in rows
    ]


@avaliacoes.patch("/{avaliacao_id}", response_model=AvaliacaoAdminItem)
async def moderar_avaliacao(
    avaliacao_id: uuid.UUID,
    body: AvaliacaoStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Aprova ou oculta (Pendente) uma avaliação."""
    av = await db.get(Avaliacao, avaliacao_id)
    if av is None:
        raise _err(404, "NAO_ENCONTRADO", "Avaliação não encontrada.")
    av.status = body.status
    await db.commit()
    aluno = await db.get(Aluno, av.aluno_id)
    curso = await db.get(Curso, av.curso_id)
    return AvaliacaoAdminItem(
        id=av.id,
        aluno_nome=aluno.nome if aluno else "—",
        curso_titulo=curso.titulo if curso else "—",
        nota=av.nota, texto=av.texto, status=av.status, criado_em=av.criado_em,
    )


@avaliacoes.delete("/{avaliacao_id}", status_code=204)
async def excluir_avaliacao(avaliacao_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    av = await db.get(Avaliacao, avaliacao_id)
    if av is None:
        raise _err(404, "NAO_ENCONTRADO", "Avaliação não encontrada.")
    await db.delete(av)
    await db.commit()
    return Response(status_code=204)


router.include_router(avaliacoes)


# ── Cupons de desconto (Stripe Coupon + Promotion Code) ───────────────────────
# Só Administrador: cupom mexe em RECEITA (desconto). Editor cuida de conteúdo,
# não de descontos — reduz o risco de insider dar desconto preferencial.
cupons = APIRouter(prefix="/cupons", dependencies=[Depends(require_papel(*_SO_ADMIN))])


@cupons.get("", response_model=list[CupomAdmin])
async def listar_cupons(db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(select(Cupom).order_by(Cupom.criado_em.desc()))
    ).scalars().all()


@cupons.post("", response_model=CupomAdmin, status_code=201)
async def criar_cupom(body: CupomCreate, db: AsyncSession = Depends(get_db)):
    if not stripe_ativo():
        raise _err(
            400, "STRIPE_NAO_CONFIGURADO",
            "Sem Stripe configurado: o cupom não teria efeito no checkout.",
        )
    # RESERVA o código no banco ANTES de tocar a Stripe: assim uma corrida no
    # `codigo` (unique) é barrada aqui (409) sem deixar um Coupon órfão na Stripe.
    obj = Cupom(**body.model_dump())
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise _err(409, "CODIGO_EM_USO", "Já existe um cupom com esse código.")

    validade_ts = int(body.validade.timestamp()) if body.validade else None
    try:
        coupon_id, promo_id = await criar_cupom_stripe(
            body.codigo, body.tipo, float(body.valor),
            max_resgates=body.max_resgates, validade_ts=validade_ts,
        )
    except stripe.error.StripeError:
        await db.rollback()  # desfaz a reserva — nada commitado
        raise _err(502, "STRIPE_ERRO", "Falha ao criar o cupom na Stripe — nada salvo.")
    obj.stripe_coupon_id = coupon_id
    obj.stripe_promotion_code_id = promo_id
    await db.commit()
    await db.refresh(obj)
    return obj


@cupons.patch("/{cupom_id}", response_model=CupomAdmin)
async def atualizar_cupom(
    cupom_id: uuid.UUID, body: CupomUpdate, db: AsyncSession = Depends(get_db)
):
    obj = await db.get(Cupom, cupom_id)
    if obj is None:
        raise _err(404, "NAO_ENCONTRADO", "Cupom não encontrado.")
    data = body.model_dump(exclude_unset=True)
    # ativo sincroniza com o Promotion Code (liga/desliga o uso no checkout).
    if "ativo" in data and obj.stripe_promotion_code_id and stripe_ativo():
        try:
            await set_cupom_ativo(obj.stripe_promotion_code_id, bool(data["ativo"]))
        except stripe.error.StripeError:
            raise _err(502, "STRIPE_ERRO", "Falha ao sincronizar com a Stripe.")
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@cupons.delete("/{cupom_id}", status_code=204)
async def excluir_cupom(cupom_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Cupom, cupom_id)
    if obj is None:
        raise _err(404, "NAO_ENCONTRADO", "Cupom não encontrado.")
    if stripe_ativo():
        await arquivar_cupom_stripe(obj.stripe_promotion_code_id)  # best-effort
    await db.delete(obj)
    await db.commit()
    return Response(status_code=204)


router.include_router(cupons)


# ── Reembolsos (cancelamento pelo suporte) ────────────────────────────────────
# Sem trava de 7 dias: a janela é o DIREITO do aluno; o suporte pode reembolsar
# a qualquer tempo (cortesia/exceção). Papéis: Administrador e Suporte.
reembolsos = APIRouter(prefix="/reembolsos", dependencies=[Depends(require_papel(*_ALUNOS))])


@reembolsos.get("", response_model=AlunoReembolsos)
async def buscar_reembolsos(
    email: EmailStr = Query(..., description="E-mail do aluno"),
    db: AsyncSession = Depends(get_db),
):
    aluno = (
        await db.execute(select(Aluno).where(Aluno.email == email))
    ).scalar_one_or_none()
    if aluno is None:
        raise _err(404, "ALUNO_NAO_ENCONTRADO", "Nenhum aluno com esse e-mail.")

    mats = (
        await db.execute(
            select(Matricula)
            .where(Matricula.aluno_id == aluno.id)
            .options(selectinload(Matricula.curso))
            .order_by(Matricula.data_inicio.desc())
        )
    ).scalars().all()
    pag_ids = [m.pagamento_id for m in mats if m.pagamento_id]
    pagamentos: dict = {}
    if pag_ids:
        rows = (
            await db.execute(select(Pagamento).where(Pagamento.id.in_(pag_ids)))
        ).scalars().all()
        pagamentos = {p.id: p for p in rows}

    agora = datetime.now(timezone.utc)
    items = []
    for m in mats:
        pag = pagamentos.get(m.pagamento_id) if m.pagamento_id else None
        limite = limite_cancelamento(pag)
        if pag is None:
            origem = "manual"
        elif m.stripe_subscription_id:
            origem = "assinatura"
        else:
            origem = "avulsa"
        items.append(ReembolsoItem(
            matricula_id=m.id,
            curso_titulo=m.curso.titulo,
            status=m.status.value,
            origem=origem,
            valor=float(pag.valor) if pag else None,
            pago_em=pag.criado_em if pag else None,
            dentro_da_janela=bool(limite is not None and agora <= limite),
            cancelavel=(
                pag is not None
                and pag.status == StatusPagamento.aprovado
                and pag.gateway == "stripe"
                and m.status == StatusMatricula.ativo
            ),
        ))
    return AlunoReembolsos(
        aluno_id=aluno.id, nome=aluno.nome, email=aluno.email, matriculas=items
    )


@reembolsos.post("/{matricula_id}/cancelar", response_model=CancelamentoResultado)
async def cancelar_matricula_admin(
    matricula_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    # Trava a linha (FOR UPDATE) antes de checar o status: dois operadores não
    # estornam a mesma matrícula em paralelo (anti duplo reembolso).
    mat = (
        await db.execute(
            select(Matricula).where(Matricula.id == matricula_id).with_for_update()
        )
    ).scalar_one_or_none()
    if mat is None:
        raise _err(404, "MATRICULA_NAO_ENCONTRADA", "Matrícula não encontrada.")
    if mat.status != StatusMatricula.ativo:
        raise _err(409, "MATRICULA_NAO_ATIVA", "Esta matrícula não está ativa.")
    pag = await db.get(Pagamento, mat.pagamento_id) if mat.pagamento_id else None
    if pag is None or pag.status != StatusPagamento.aprovado or pag.gateway != "stripe":
        raise _err(
            409, "SEM_PAGAMENTO_REEMBOLSAVEL",
            "Não há pagamento online aprovado vinculado a esta matrícula.",
        )
    if not stripe_ativo():
        raise _err(503, "STRIPE_NAO_CONFIGURADO", "Reembolsos indisponíveis no momento.")

    try:
        assinatura_cancelada, cursos_revogados = await executar_cancelamento(db, mat, pag)
    except stripe.error.StripeError:
        raise _err(502, "STRIPE_ERRO", "Falha ao processar o reembolso — nada foi alterado.")

    await db.commit()
    return CancelamentoResultado(
        matricula_id=mat.id,
        reembolsado=True,
        assinatura_cancelada=assinatura_cancelada,
        cursos_revogados=cursos_revogados,
    )


router.include_router(reembolsos)


# ── Upload de imagens (capa de curso → Supabase Storage) ──────────────────────
uploads = APIRouter(prefix="/uploads", dependencies=[Depends(require_papel(*_CONTEUDO))])


@uploads.post("/imagem")
@limiter.limit("30/minute")
async def upload_imagem_admin(request: Request, arquivo: UploadFile = File(...)):
    """Recebe a imagem do painel, sobe ao Supabase Storage e devolve a URL
    pública (que o admin grava em `thumbnail_url` do curso).

    Só raster (PNG/JPG/WebP) até 5 MB, validado por magic bytes em `upload_imagem`.
    A leitura é limitada para não bufferizar um upload gigante na memória.
    """
    if not storage_ativo():
        raise _err(
            503, "STORAGE_NAO_CONFIGURADO",
            "Upload de imagens indisponível — configure o Supabase Storage.",
        )
    # Lê no máximo 5 MB + 1 byte: se vier mais, recusa sem bufferizar o resto.
    conteudo = await arquivo.read(MAX_BYTES + 1)
    if len(conteudo) > MAX_BYTES:
        raise _err(413, "IMAGEM_GRANDE", "Imagem acima de 5 MB.")
    try:
        url = await upload_imagem(conteudo, arquivo.content_type, "cursos")
    except StorageError as exc:
        raise _err(400, "UPLOAD_INVALIDO", str(exc))
    return {"url": url}


router.include_router(uploads)


# ── Administradores (equipe) — create/patch tratam senha ──────────────────────
admins = APIRouter(prefix="/administradores", dependencies=[Depends(require_papel(*_SO_ADMIN))])


@admins.get("", response_model=list[AdminUserItem])
async def listar_admins(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Admin).order_by(Admin.criado_em.desc()))).scalars().all()


@admins.post("", response_model=AdminUserItem, status_code=201)
async def criar_admin(body: AdminUserCreate, db: AsyncSession = Depends(get_db)):
    if await db.scalar(select(Admin.id).where(Admin.email == body.email)):
        raise _err(409, "EMAIL_EM_USO", "Já existe um administrador com esse e-mail.")
    obj = Admin(
        nome=body.nome,
        email=body.email,
        senha_hash=hash_password(body.senha),
        papel=body.papel,
        ativo=body.ativo,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@admins.patch("/{admin_id}", response_model=AdminUserItem)
async def atualizar_admin(
    admin_id: uuid.UUID,
    body: AdminUserUpdate,
    atual: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    obj = await db.get(Admin, admin_id)
    if obj is None:
        raise _err(404, "NAO_ENCONTRADO", "Administrador não encontrado.")
    data = body.model_dump(exclude_unset=True)
    # Não pode alterar o próprio papel (evita auto-rebaixamento/lock-out).
    if admin_id == atual.id and data.get("papel") not in (None, obj.papel):
        raise _err(409, "AUTO_ALTERACAO_PAPEL", "Você não pode alterar o próprio papel.")
    if "email" in data and data["email"] != obj.email:
        if await db.scalar(select(Admin.id).where(Admin.email == data["email"])):
            raise _err(409, "EMAIL_EM_USO", "E-mail já em uso.")
    if "senha" in data:
        senha = data.pop("senha")
        if senha:
            obj.senha_hash = hash_password(senha)
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@admins.delete("/{admin_id}", status_code=204)
async def excluir_admin(
    admin_id: uuid.UUID,
    atual: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if admin_id == atual.id:
        raise _err(409, "AUTO_EXCLUSAO", "Você não pode excluir a própria conta.")
    obj = await db.get(Admin, admin_id)
    if obj is None:
        raise _err(404, "NAO_ENCONTRADO", "Administrador não encontrado.")
    await db.delete(obj)
    await db.commit()
    return Response(status_code=204)


router.include_router(admins)
