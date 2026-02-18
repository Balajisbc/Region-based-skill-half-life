"""AI assistant chat API route declarations."""

from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/status", summary="Chat module health")
def chat_status() -> dict[str, str]:
	"""Return chat module readiness status."""
	return {"module": "chat", "status": "ready"}
