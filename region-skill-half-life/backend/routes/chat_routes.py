from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from services.intelligence_engine import generate_response

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str | None = None


class VoiceRequest(BaseModel):
    text: str
    language: str = "en-US"


@router.post("/chat")
@router.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        message = (request.message or "").strip()
        if not message:
            return {"response": "Please provide a message."}

        response_text = generate_response(message)
        return {"response": response_text}
    except Exception:
        return {"response": "Server unavailable. Please try again."}


@router.post("/voice")
def voice(request: VoiceRequest):
    print("Route hit: /voice")
    return {
        "language": request.language,
        "transcript": request.text,
        "speak_text": request.text,
        "audio_supported": False,
        "message": "Voice synthesis should be handled in browser Web Speech APIs.",
    }
