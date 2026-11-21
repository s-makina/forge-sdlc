"""Health route."""

from fastapi import APIRouter

from app.core.container import Container, get_container

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    """Report process health and Temporal connectivity."""
    container: Container = get_container()
    return {
        "status": "ok",
        "temporal": container.orchestrator.healthy(),
    }