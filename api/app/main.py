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


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception as exc:  # surfaced, not swallowed — a demo with no DB is not "ok"
        database = f"error: {exc.__class__.__name__}"

    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "version": __version__,
    }
