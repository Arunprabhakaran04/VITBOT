from fastapi import FastAPI
from backend.app.routers import users, chat, pdf_celery as pdf
from backend.database_connection import get_connection_pool, close_connection_pool
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database connection pool on startup"""
    get_connection_pool()

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection pool on shutdown"""
    close_connection_pool()

app.include_router(users.router)
app.include_router(chat.router)
app.include_router(pdf.router)
