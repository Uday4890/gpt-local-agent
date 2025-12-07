from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from .database import engine, Base
from .routers import posts

# Initialize the database
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Blog API",
    description="A production-ish blog API using FastAPI and SQLite",
    version="1.0.0",
)

# Set up CORS (allow all origins, methods, headers for demo, adjust in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the posts router
app.include_router(posts.router, prefix="/posts", tags=["posts"])

# Basic logging config
logging.basicConfig(level=logging.INFO)

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
