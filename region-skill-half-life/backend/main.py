from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat_routes import router as chat_router

from routes import (
    analytics_routes,
    auth_routes,
    chat_routes,
    comparison_routes,
    region_routes,
    report_routes,
    simulation_routes,
)

app = FastAPI()
app.include_router(chat_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    print("Route hit: /")
    return {"status": "Backend running"}


app.include_router(auth_routes)
app.include_router(analytics_routes)
app.include_router(region_routes)
app.include_router(chat_routes)
app.include_router(report_routes)
app.include_router(comparison_routes)
app.include_router(simulation_routes)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
