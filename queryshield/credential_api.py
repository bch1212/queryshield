"""HTTP surface for the named credential vault.

Admin routes use ``X-Admin-Key``. Agent routes use the same ``X-API-Key``
as ``/v1/query`` — there is no second key prefix. Plaintext values are
returned only from the agent reveal route.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, Response
from pydantic import BaseModel, Field

from queryshield import auth as qs_auth
from queryshield.credentials import (
    CredentialError,
    budget_summary,
    create_credential,
    delete_credential,
    get_credential,
    list_access_log,
    list_available_names,
    list_credentials,
    reveal_credential,
    update_agent_vault,
    update_credential,
)
from queryshield.models import Agent
from queryshield.rate_limit import check as rl_check, client_ip


class CredentialCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)
    provider: Optional[str] = None
    rotation_interval_hours: Optional[int] = None
    metadata: dict = Field(default_factory=dict)


class CredentialUpdateBody(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    value: Optional[str] = None
    rotation_interval_hours: Optional[int] = None
    metadata: Optional[dict] = None


class AgentVaultUpdateBody(BaseModel):
    name: Optional[str] = None
    credential_permissions: Optional[list[str]] = None
    budget_daily: Optional[float] = None
    budget_monthly: Optional[float] = None
    active: Optional[bool] = None


def _raise(exc: CredentialError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def build_credential_router(require_admin, require_agent):  # type: ignore[no-untyped-def]
    router = APIRouter()

    @router.post("/v1/credentials", status_code=201)
    async def create_named_credential(
        body: CredentialCreateBody, admin: Agent = Depends(require_admin)
    ):
        try:
            return create_credential(
                admin.tenant_id,
                body.name,
                body.value,
                provider=body.provider,
                rotation_interval_hours=body.rotation_interval_hours,
                metadata=body.metadata,
            )
        except CredentialError as e:
            _raise(e)

    @router.get("/v1/credentials")
    async def list_named_credentials(admin: Agent = Depends(require_admin)):
        return {"credentials": list_credentials(admin.tenant_id)}

    @router.get("/v1/credentials/access-log")
    async def credential_access_log(limit: int = 100, admin: Agent = Depends(require_admin)):
        return {"entries": list_access_log(admin.tenant_id, limit)}

    @router.get("/v1/credentials/{credential_id}")
    async def get_named_credential(credential_id: str, admin: Agent = Depends(require_admin)):
        try:
            return get_credential(admin.tenant_id, credential_id)
        except CredentialError as e:
            _raise(e)

    @router.patch("/v1/credentials/{credential_id}")
    async def patch_named_credential(
        credential_id: str,
        body: CredentialUpdateBody,
        admin: Agent = Depends(require_admin),
    ):
        try:
            return update_credential(
                admin.tenant_id,
                credential_id,
                name=body.name,
                provider=body.provider,
                value=body.value,
                rotation_interval_hours=body.rotation_interval_hours,
                metadata=body.metadata,
                fields_set=set(body.model_fields_set),
            )
        except CredentialError as e:
            _raise(e)

    @router.delete("/v1/credentials/{credential_id}", status_code=204)
    async def remove_named_credential(credential_id: str, admin: Agent = Depends(require_admin)):
        try:
            delete_credential(admin.tenant_id, credential_id)
        except CredentialError as e:
            _raise(e)
        return Response(status_code=204)

    @router.patch("/v1/agents/{agent_id}")
    async def patch_agent_vault(
        agent_id: str,
        body: AgentVaultUpdateBody,
        admin: Agent = Depends(require_admin),
    ):
        try:
            return update_agent_vault(
                admin.tenant_id,
                agent_id,
                name=body.name,
                credential_permissions=body.credential_permissions,
                budget_daily=body.budget_daily,
                budget_monthly=body.budget_monthly,
                active=body.active,
                fields_set=set(body.model_fields_set),
            )
        except CredentialError as e:
            _raise(e)

    @router.get("/v1/agents/{agent_id}/budget")
    async def get_agent_budget(agent_id: str, admin: Agent = Depends(require_admin)):
        try:
            return budget_summary(admin.tenant_id, agent_id)
        except CredentialError as e:
            _raise(e)

    @router.post("/v1/vault/get/{credential_name}")
    async def vault_get(
        credential_name: str,
        request: Request,
        cost: float = 0.0,
        agent: Agent = Depends(require_agent),
    ):
        ip = client_ip(request)
        allowed, retry = rl_check(ip, "vault_get", limit=120, window_sec=60)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={"reason": "ip rate limit", "retry_after_sec": retry},
                headers={"Retry-After": str(retry)},
            )
        try:
            return reveal_credential(
                agent.id,
                credential_name,
                cost=cost,
                ip_address=ip,
                user_agent=request.headers.get("user-agent"),
            )
        except CredentialError as e:
            _raise(e)

    @router.get("/v1/vault/credentials")
    async def vault_list(agent: Agent = Depends(require_agent)):
        try:
            return {"credentials": list_available_names(agent.id)}
        except CredentialError as e:
            _raise(e)

    def _tenant_from_session(
        qs_session: str | None = Cookie(default=None, alias=qs_auth.SESSION_COOKIE),
    ) -> str:
        tenant_id = qs_auth.verify_session(qs_session)
        if tenant_id is None:
            raise HTTPException(status_code=401, detail="not authenticated")
        return tenant_id

    @router.post("/dashboard/credentials")
    async def dashboard_store_credential(
        name: str = Form(...),
        value: str = Form(...),
        provider: str = Form(""),
        tenant_id: str = Depends(_tenant_from_session),
    ):
        try:
            created = create_credential(
                tenant_id,
                name,
                value,
                provider=provider or None,
            )
        except CredentialError as e:
            _raise(e)
        return {"id": created["id"], "name": created["name"], "ok": True}

    @router.delete("/dashboard/credentials/{credential_id}")
    async def dashboard_delete_credential(
        credential_id: str,
        tenant_id: str = Depends(_tenant_from_session),
    ):
        try:
            delete_credential(tenant_id, credential_id)
        except CredentialError as e:
            _raise(e)
        return {"id": credential_id, "deleted": True}

    return router
