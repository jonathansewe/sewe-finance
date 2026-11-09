"""GET /api/v1/health: is the API up, and can it reach the database?

Hosting platforms and uptime monitors call this. It answers 200 only when
a real query succeeds, so "API up but database down" shows as 503 instead
of looking healthy.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Session = Depends(get_session)) -> JSONResponse:  # noqa: B008
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Never echo the error: it can contain the connection string.
        return JSONResponse(status_code=503, content={"status": "error", "database": "down"})
    return JSONResponse(content={"status": "ok", "database": "ok"})
