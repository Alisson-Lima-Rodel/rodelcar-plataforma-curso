import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.ratelimit import auth_limit, limiter
from app.core.security import create_admin_token, hash_password, verify_password
from app.dependencies import get_current_admin, require_papel
from app.models import (
    Admin,
    Aluno,
    Aula,
    Curso,
    Depoimento,
    Faq,
    Matricula,
    Modulo,
    Pacote,
    PapelAdmin,
    StatusMatricula,
    Video,
)

# Escopos de papel (RBAC). Administrador faz tudo; Editor cuida de conteúdo
# (cursos/pacotes/depoimentos/vídeos/FAQ); Suporte cuida de alunos.
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
    PacoteAdmin,
    PacoteCreate,
    PacoteUpdate,
    VideoAdmin,
    VideoCreate,
    VideoUpdate,
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
    if admin is None or not admin.ativo or not verify_password(body.senha, admin.senha_hash):
        raise _err(401, "CREDENCIAIS_INVALIDAS", "E-mail ou senha incorretos.")
    admin.ultimo_acesso = datetime.now(timezone.utc)
    await db.commit()
    return AdminTokenResponse(
        access_token=create_admin_token(str(admin.id)),
        expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
    )


@router.get("/auth/me", response_model=AdminMe)
async def admin_me(admin: Admin = Depends(get_current_admin)):
    return admin


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
    db.add(curso)
    await db.commit()
    await db.refresh(curso)
    return curso


@cursos.patch("/{curso_id}", response_model=CursoAdmin)
async def atualizar_curso(curso_id: uuid.UUID, body: CursoUpdate, db: AsyncSession = Depends(get_db)):
    curso = await db.get(Curso, curso_id)
    if curso is None:
        raise _err(404, "CURSO_NAO_ENCONTRADO", "Curso não encontrado.")
    data = body.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] != curso.slug:
        if await db.scalar(select(Curso.id).where(Curso.slug == data["slug"])):
            raise _err(409, "SLUG_EM_USO", "Já existe um curso com esse slug.")
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


# ── CRUD genérico p/ cadastros simples (Depoimentos, Pacotes) ─────────────────
def _crud_router(prefix, model, read_schema, create_schema, update_schema, papeis=_CONTEUDO):
    r = APIRouter(prefix=prefix, dependencies=[Depends(require_papel(*papeis))])

    @r.get("", response_model=list[read_schema])
    async def listar(db: AsyncSession = Depends(get_db)):
        return (await db.execute(select(model).order_by(model.ordem, model.criado_em))).scalars().all()

    @r.post("", response_model=read_schema, status_code=201)
    async def criar(body: create_schema, db: AsyncSession = Depends(get_db)):  # type: ignore[valid-type]
        obj = model(**body.model_dump())
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    @r.patch("/{obj_id}", response_model=read_schema)
    async def atualizar(obj_id: uuid.UUID, body: update_schema, db: AsyncSession = Depends(get_db)):  # type: ignore[valid-type]
        obj = await db.get(model, obj_id)
        if obj is None:
            raise _err(404, "NAO_ENCONTRADO", "Registro não encontrado.")
        for k, v in body.model_dump(exclude_unset=True).items():
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


router.include_router(_crud_router("/depoimentos", Depoimento, DepoimentoAdmin, DepoimentoCreate, DepoimentoUpdate))
router.include_router(_crud_router("/pacotes", Pacote, PacoteAdmin, PacoteCreate, PacoteUpdate))
router.include_router(_crud_router("/videos", Video, VideoAdmin, VideoCreate, VideoUpdate))
router.include_router(_crud_router("/faqs", Faq, FaqAdmin, FaqCreate, FaqUpdate))


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
