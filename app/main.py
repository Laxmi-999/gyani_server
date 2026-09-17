from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.database import Base, engine
from app.models.file import FileAttachment
from app.routers import auth, files, notes
from app.services.embedding import get_embedding_model

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup phase: Load ML model before accepting incoming traffic
    get_embedding_model()
    yield
    # Cleanup phase

# Pass lifespan into the FastAPI constructor
app = FastAPI(title="Gyani API", version="0.1.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(files.router)

@app.get("/")
def home():
    return {"Hello world"}

app = CORSMiddleware(
    app=app,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)