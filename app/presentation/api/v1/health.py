from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "market-backend",
        "version": "0.1.0",
    }
