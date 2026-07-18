import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.rbac import require_min_level
from src.core.config import settings as app_settings
from src.core.database import get_session
from src.core.services.rag_service import execute_query

logger = logging.getLogger("nexus")
router = APIRouter(prefix="/api/v1/rag")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    document_ids: list[int] = Field(..., min_length=1)


class QueryResponse(BaseModel):
    answer: str
    context_used: list[str]


@router.post("/query", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    _user: dict = Depends(require_min_level(1)),
    db: AsyncSession = Depends(get_session),
):
    settings = app_settings
    result = await execute_query(
        db=db,
        query_text=body.query,
        document_ids=body.document_ids,
        user=_user,
        ollama_host=settings.ollama_host,
        model_name=settings.model_name,
    )
    logger.info(
        "RAG query: user=%s docs=%s",
        _user.get("sub"),
        body.document_ids,
    )
    return QueryResponse(**result)
