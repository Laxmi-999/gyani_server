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

app = FastAPI(title="Gyani API", version="0.1.0")

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


# Keep CORS outside the application so even error responses from mutations
# retain the headers the browser needs to report the real API error.
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
