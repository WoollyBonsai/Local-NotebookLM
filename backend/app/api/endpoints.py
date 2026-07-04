from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from app.agents.processor import process_pdf
from app.database.vector import search_vector_db, collection
from app.database.models import SessionLocal, Concept, Document
from litellm import completion
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

class QueryRequest(BaseModel):
    query: str
    sources: Optional[List[int]] = None

@router.post("/clear")
def clear_databases():
    db = SessionLocal()
    try:
        db.query(Concept).delete()
        db.query(Document).delete()
        db.commit()
    except Exception:
        pass
    finally:
        db.close()
        
    try:
        existing_docs = collection.get()
        if existing_docs and existing_docs['ids']:
            collection.delete(ids=existing_docs['ids'])
    except Exception:
        pass
        
    return {"message": "Databases cleared"}

@router.get("/sources")
def get_sources():
    db = SessionLocal()
    docs = db.query(Document).all()
    sources = [{"id": d.id, "filename": d.filename} for d in docs]
    db.close()
    return {"sources": sources}

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    process_pdf(file_path, file.filename)
    
    return {"message": "File uploaded and processed successfully", "filename": file.filename}

@router.post("/query")
async def query_tutor(request: QueryRequest):
    query = request.query
    sources = request.sources
    
    db = SessionLocal()
    stop_words = {"what", "is", "the", "a", "an", "of", "in", "to", "for", "and", "about", "tell", "me", "how"}
    query_terms = [t for t in query.lower().split() if t not in stop_words and len(t) > 2]
    
    matched_concept = None
    concepts_query = db.query(Concept)
    if sources:
        concepts_query = concepts_query.filter(Concept.document_id.in_(sources))
    concepts = concepts_query.all()
    
    best_match_score = 0
    for c in concepts:
        score = sum(1 for term in query_terms if term in c.name.lower())
        if score > best_match_score:
            best_match_score = score
            matched_concept = c
            
    db.close()
    
    context = ""
    citations = []
    
    if matched_concept:
        context += f"Verified Concept: {matched_concept.name}\nFact/Definition: {matched_concept.definition}\n\n"
        citations.append(f"Document Graph (Page {matched_concept.page_number})")
        
    # Optional filtering in ChromaDB based on filenames
    where_clause = None
    if sources:
        db = SessionLocal()
        docs = db.query(Document).filter(Document.id.in_(sources)).all()
        filenames = [d.filename for d in docs]
        db.close()
        if len(filenames) == 1:
            where_clause = {"filename": filenames[0]}
        elif len(filenames) > 1:
            where_clause = {"filename": {"$in": filenames}}
            
    vector_results = search_vector_db(query, n_results=3, where=where_clause)
    if vector_results and vector_results.get('documents') and vector_results['documents'][0]:
        vector_context = "\n---\n".join(vector_results['documents'][0])
        context += f"Semantic Context:\n{vector_context}\n"
        citations.append("Vector Search")
        
    if not context.strip():
        return {"response": "I do not have enough verified context in my knowledge base to answer this securely. (Anti-Hallucination Guardrail Triggered)"}
        
    citation_str = " & ".join(citations)

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

class ActionRequest(BaseModel):
    action_type: str
    sources: Optional[List[int]] = None

@router.post("/action")
async def predefined_action(request: ActionRequest):
    db = SessionLocal()
    concepts_query = db.query(Concept)
    if request.sources:
        concepts_query = concepts_query.filter(Concept.document_id.in_(request.sources))
    concepts = concepts_query.all()
    db.close()

    if not concepts:
        return {"response": "No concepts available for this action. Please upload and select a document."}

    context = "\n".join([f"- {c.name}: {c.definition}" for c in concepts])
    
    if request.action_type == "report":
        task = "Write a comprehensive summary report based on the following concepts."
    elif request.action_type == "quiz":
        task = "Generate a 3-question multiple choice quiz based on the following concepts. Include an answer key at the bottom."
    elif request.action_type == "keywords":
        task = "List all the key terms and provide a one-sentence simple definition for each based on the context."
    else:
        return {"response": "Unknown action type"}
        
    prompt = f"""
    You are EduGuard, an AI Tutor.
    Task: {task}
    
    Context:
    {context}
    """
    
    try:
        response = completion(
            model="ollama/llama3.1",
            api_base=OLLAMA_API_BASE,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        return {"response": response.choices[0].message.content.strip()}
    except Exception as e:
        return {"response": f"Error performing action: {e}"}

