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
    
    # 1. Smarter keyword matching: ignore common stop words
    stop_words = {"what", "is", "the", "a", "an", "of", "in", "to", "for", "and", "about", "tell", "me", "how"}
    query_terms = [t for t in query.lower().split() if t not in stop_words and len(t) > 2]
    
    matched_concept = None
    concepts = db.query(Concept).all()
    
    # Find the concept with the most matching terms
    best_match_score = 0
    for c in concepts:
        score = sum(1 for term in query_terms if term in c.name.lower())
        if score > best_match_score:
            best_match_score = score
            matched_concept = c
            
    db.close()
    
    context = ""
    citations = []
    
    # 2. Add Graph Context if matched
    if matched_concept:
        context += f"Verified Concept: {matched_concept.name}\nFact/Definition: {matched_concept.definition}\n\n"
        citations.append(f"Document Graph (Page {matched_concept.page_number})")
        
    # 3. Always add Vector Context for deeper details
    vector_results = search_vector_db(query, n_results=3)
    if vector_results and vector_results['documents'] and vector_results['documents'][0]:
        vector_context = "\n---\n".join(vector_results['documents'][0])
        context += f"Semantic Context:\n{vector_context}\n"
        citations.append("Vector Search")
        
    if not context.strip():
        return {"response": "I do not have enough verified context in my knowledge base to answer this securely. (Anti-Hallucination Guardrail Triggered)"}
        
    citation_str = " & ".join(citations)

    # Use LLM to synthesize answer
    prompt = f"""
    You are EduGuard, an AI Tutor. Answer the user's question using ONLY the provided context below.
    If the context does not contain the answer, explicitly state that you don't know based on the provided documents.
    
    Context:
    {context}
    
    Question: {query}
    """
    
    try:
        response = completion(
            model="ollama/llama3.1",
            api_base=OLLAMA_API_BASE,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )
        answer = response.choices[0].message.content.strip()
        return {"response": f"{answer}\n\n[Source: {citation_str}]"}
    except Exception as e:
        return {"response": f"Error synthesizing answer: {e}"}

