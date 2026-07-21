import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from src.routers.auth import router as auth_router

app = FastAPI(
    title="Feedback API",
    description="REST API для системы обратной связи с JWT-аутентификацией",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[""],
    allow_credentials=True,
    allow_methods=[""],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/", tags=["Health"], summary="Health check")
async def root():
    return {"status": "ok", "message": "Feedback API v2.0 is running 🚀"}

if __name__ == '__main__':
    uvicorn.run("src.main:app", reload=True, host="0.0.0.0", port=8000)