from fastapi import FastAPI
from fastapi.middleware.cors import  CORSMiddleware
from app.routers import auth, notes,files
from app.models.file import FileAttachment
from app.database import engine, Base
from contextlib import asynccontextmanager
from app.services.embedding import get_embedding_model

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup phase: Load ML model Before accepting incomming traffic
    get_embedding_model()
    yield
    # clean-up

app = FastAPI(title = "Gyani API", version = "0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(files.router)

@app.get("/")
def home():
    print("welcome to home")
    return {"Hello world"}


@app.get("/health")
def health():
    return {"status": "ok"}
