from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Report that the API process is running."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    """Report process readiness; external dependency checks are not configured yet."""
    return {"status": "ready"}
