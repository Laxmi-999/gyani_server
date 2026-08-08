from fastapi import FastAPI
from fastapi.middleware.cors import  CORSMiddleware
from app.routers import auth

app = FastAPI(title = "Gyani API", version = "0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["https://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"], # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"], # Allows all headers like Content-Type, Authorization

)
app.include_router(auth.router)
@app.get("/")
def home():
    print("welcome to home")
    return {"Hello world"}


@app.get("/health")
def health():
    return {"status": "ok"}
