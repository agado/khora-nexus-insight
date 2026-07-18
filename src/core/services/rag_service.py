import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import AuditLog, Document


def _build_prompt(query: str, context_chunks: list[str]) -> str:
    context = "\n---\n".join(context_chunks)
    return (
        f"<contexto>\n{context}\n</contexto>\n"
        f"<pregunta>\n{query}\n</pregunta>\n"
        "Instrucción: Responde basándote exclusivamente en el contexto anterior."
    )


async def execute_query(
    db: AsyncSession,
    query_text: str,
    document_ids: list[int],
    user: dict,
    ollama_host: str,
    model_name: str,
) -> dict:
    allowed = user.get("accessible_departments", [])

    result = await db.execute(
        select(Document).where(
            Document.id.in_(document_ids),
            Document.department_id.in_(allowed),
            Document.content_text.isnot(None),
        )
    )
    docs = list(result.scalars().all())

    context_chunks = [d.content_text for d in docs if d.content_text]
    prompt = _build_prompt(query_text, context_chunks)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{ollama_host}/api/generate",
            json={"model": model_name, "prompt": prompt, "stream": False},
        )
    resp.raise_for_status()
    answer = resp.json().get("response", "")

    log = AuditLog(
        action="rag_query",
        user_id=user["user_id"],
        metadata_={"query": query_text, "document_ids": document_ids},
    )
    db.add(log)
    await db.flush()

    return {"answer": answer, "context_used": context_chunks}
