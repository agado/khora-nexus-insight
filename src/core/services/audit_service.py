from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: int,
    metadata: dict | None = None,
) -> None:
    db.add(AuditLog(action=action, user_id=user_id, metadata_=metadata))
