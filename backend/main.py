from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.routers import chat_router, webhook_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router.router)
app.include_router(webhook_router.router)

# Serve the frontend statically (html=True automatically serves index.html at /)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
