from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/providers")


@router.get("")
async def list_providers(request: Request) -> list[dict[str, str | bool]]:
    return request.app.state.provider_registry.list_public()
