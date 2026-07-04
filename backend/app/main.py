from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI(title="EduGuard Auto-Tutor API", description="Backend for local NotebookLM alternative")

# Configure CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "EduGuard API is running!"}

@app.get("/health")
def health_check():
    return {"status": "ok", "cloud_endpoint": os.getenv("OLLAMA_API_BASE", "Not Set")}
