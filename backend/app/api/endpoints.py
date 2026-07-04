from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os

router = APIRouter()

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # TODO: Trigger background task to parse PDF, chunk into ChromaDB, and build SQLite Graph
    
    return {"message": "File uploaded successfully", "filename": file.filename}

@router.post("/query")
async def query_tutor(query: str):
    # TODO: Query SQLite Graph -> if verified, query Local LLM or Cloud LLM -> Return answer
    return {"response": f"You asked: {query} (This is a mock response from EduGuard)"}
