from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/ping")
def auth_ping():
    print("Route hit: /auth/ping")
    return {"status": "ok", "message": "auth routes online"}
