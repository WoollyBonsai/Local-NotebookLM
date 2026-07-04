from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import shutil
import os
from app.agents.processor import process_pdf
from app.database.vector import search_vector_db
from app.database.models import SessionLocal, Concept
from litellm import completion

router = APIRouter()

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

@router.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Trigger background task to parse PDF, chunk into ChromaDB, and build SQLite Graph
    background_tasks.add_task(process_pdf, file_path, file.filename)
    
    return {"message": "File uploaded successfully", "filename": file.filename}

@router.post("/query")
async def query_tutor(query: str):
    db = SessionLocal()
    
    # Anti-Hallucination Guardrail: Attempt to find a relational concept matching the query terms
    # For a real system we'd extract entities from the query first. For now, basic term matching.
    query_terms = query.lower().split()
    matched_concept = None
    
    concepts = db.query(Concept).all()
    for c in concepts:
        if any(term in c.name.lower() for term in query_terms if len(term) > 4):
            matched_concept = c
            break
            
    db.close()
    
    if not matched_concept:
        # Fallback to vector search if no direct graph link found
        vector_results = search_vector_db(query, n_results=2)
        if not vector_results['documents'][0]:
            return {"response": "I do not have enough verified context in my knowledge base to answer this securely. (Anti-Hallucination Guardrail Triggered)"}
        context = "\n".join(vector_results['documents'][0])
        citation = "Vector Search"
    else:
        context = f"Concept: {matched_concept.name}\nDefinition: {matched_concept.definition}"
        citation = f"Document Page {matched_concept.page_number}"

    # Use LLM to synthesize answer
    prompt = f"""
    You are EduGuard, an AI Tutor. Answer the user's question using ONLY the provided context.
    If the context does not contain the answer, say you don't know.
    
    Context [{citation}]:
    {context}
    
    Question: {query}
    """
    
    try:
        response = completion(
            model="ollama/llama3.1",
            api_base=OLLAMA_API_BASE,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        answer = response.choices[0].message.content.strip()
        return {"response": f"{answer}\n\n[Source: {citation}]"}
    except Exception as e:
        return {"response": f"Error synthesizing answer: {e}"}

