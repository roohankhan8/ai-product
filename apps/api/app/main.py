from fastapi import FastAPI

app = FastAPI(
    title="AI Operations API",
    description="Backend API for the AI Operations Platform.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Report that the API process is running."""
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def readiness() -> dict[str, str]:
    """Report process readiness; dependency checks can be added with the services."""
    return {"status": "ready"}
