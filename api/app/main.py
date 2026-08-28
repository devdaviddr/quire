import httpx
from fastapi import FastAPI
from sqlalchemy import create_engine, text

from app import __version__
from app.config import settings

app = FastAPI(
    title="Quire",
    version=__version__,
    summary="A prepared redaction review for FOI requests against clinical records.",
)

engine = create_engine(settings.database_url, pool_pre_ping=True)


def _check_database() -> str:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # surfaced, not swallowed — no DB is not "ok"
        return f"error: {exc.__class__.__name__}"


def _check_detector() -> str:
    """Confirm the configured model is actually served by the endpoint.

    The model catalogue is unauthenticated on NVIDIA NIM, so this validates the
    model id without spending a rate-limited inference call. A typo'd model
    name otherwise surfaces only when the first bundle is processed.
    """
    try:
        with httpx.Client(base_url=settings.llm_base_url, timeout=10) as client:
            served = {m["id"] for m in client.get("/models").json()["data"]}
    except Exception as exc:
        return f"unreachable: {exc.__class__.__name__}"

    if settings.llm_model not in served:
        return f"model not served: {settings.llm_model}"
    if not settings.llm_api_key:
        return "reachable, no api key set"
    return "ok"


@app.get("/health")
def health() -> dict[str, str]:
    database = _check_database()
    detector = _check_detector()
    healthy = database == "ok" and detector == "ok"
    return {
        "status": "ok" if healthy else "degraded",
        "database": database,
        "detector": detector,
        "model": settings.llm_model,
        "version": __version__,
    }
