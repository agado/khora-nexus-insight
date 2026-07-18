import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import AuditLog, Document


class RagConnectionError(Exception):
    """Ollama is unreachable, refused connection, or timed out."""


class RagQueryError(Exception):
    """Ollama returned a non-2xx status or an unparseable response."""


MAX_CONTEXT_CHARS = 4000


def _sanitize(text: str) -> str:
    """Strip XML closing tags to prevent prompt-injection via context boundary."""
    return text.replace("</", "")


def _build_prompt(query: str, context_chunks: list[str]) -> str:
    context = "\n---\n".join(context_chunks)
    return (
        f"<contexto>\n{context}\n</contexto>\n"
        f"<pregunta>\n{query}\n</pregunta>\n"
        "Instrucción: Responde basándote EXCLUSIVAMENTE en el contexto anterior. "
        "Si el contexto no contiene información para responder la pregunta, "
        "di 'No se encontró información relevante en los documentos seleccionados.' "
        "No inventes ni añadas información externa."
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

    context_chunks = [d.content_text[:MAX_CONTEXT_CHARS] for d in docs if d.content_text]
    safe_query = _sanitize(query_text)
    prompt = _build_prompt(safe_query, context_chunks)

    if not context_chunks:
        answer = "No se encontró contenido relevante en los documentos seleccionados."
        log = AuditLog(
            action="rag_query",
            user_id=user["user_id"],
            metadata_={
                "query": query_text,
                "document_ids": document_ids,
                "note": "empty context — no documents matched or content was null",
            },
        )
        db.add(log)
        await db.flush()
        return {"answer": answer, "context_used": []}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
            )
        resp.raise_for_status()
        answer = resp.json().get("response", "")
    except httpx.ConnectError as exc:
        raise RagConnectionError(
            "No se pudo conectar con el motor de IA (Ollama). "
            "Verifica que el contenedor esté en ejecución."
        ) from exc
    except httpx.TimeoutException as exc:
        raise RagConnectionError("La consulta al motor de IA excedió el tiempo de espera.") from exc
    except httpx.HTTPStatusError as exc:
        raise RagQueryError(f"Ollama respondió con error HTTP {exc.response.status_code}.") from exc
    except (KeyError, ValueError, TypeError) as exc:
        raise RagQueryError("El motor de IA devolvió una respuesta inesperada.") from exc

    log = AuditLog(
        action="rag_query",
        user_id=user["user_id"],
        metadata_={"query": query_text, "document_ids": document_ids},
    )
    db.add(log)
    await db.flush()

    return {"answer": answer, "context_used": context_chunks}
