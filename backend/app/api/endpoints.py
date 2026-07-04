from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from app.agents.processor import process_pdf
from app.database.vector import search_vector_db, collection
from app.database.models import SessionLocal, Concept, Document, Notebook, ChatHistory, DiaryEntry
from app.llm import call_llm, update_models
from pydantic import BaseModel
from typing import List, Optional
from fpdf import FPDF
from fastapi.responses import FileResponse
from app.config import settings

router = APIRouter()

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class EndpointUpdate(BaseModel):
    local_endpoint: str
    cloud_endpoint: str

@router.get("/config/endpoint")
def get_endpoint():
    return {
        "local_endpoint": settings.LOCAL_LLM_ENDPOINT,
        "cloud_endpoint": settings.CLOUD_LLM_ENDPOINT
    }

@router.post("/config/endpoint")
def update_endpoint(req: EndpointUpdate):
    settings.LOCAL_LLM_ENDPOINT = req.local_endpoint
    settings.CLOUD_LLM_ENDPOINT = req.cloud_endpoint
    update_models()
    return {"message": "Endpoints updated"}

# --- NOTEBOOK & CHAT ENDPOINTS ---

class NotebookCreate(BaseModel):
    name: str

class NameUpdate(BaseModel):
    name: str

@router.post("/notebooks")
def create_notebook(req: NotebookCreate):
    db = SessionLocal()
    nb = Notebook(name=req.name)
    db.add(nb)
    db.commit()
    db.refresh(nb)
    db.close()
    return {"id": nb.id, "name": nb.name}

@router.get("/notebooks")
def list_notebooks():
    db = SessionLocal()
    notebooks = db.query(Notebook).all()
    res = [{"id": n.id, "name": n.name} for n in notebooks]
    db.close()
    return {"notebooks": res}

@router.delete("/notebooks/{nb_id}")
def delete_notebook(nb_id: int):
    db = SessionLocal()
    nb = db.query(Notebook).filter(Notebook.id == nb_id).first()
    if nb:
        # Delete from ChromaDB
        for doc in nb.documents:
            try:
                res = collection.get(where={"filename": doc.filename})
                if res and res["ids"]:
                    collection.delete(ids=res["ids"])
            except Exception:
                pass
        db.delete(nb)
        db.commit()
    db.close()
    return {"message": "Notebook deleted"}

@router.put("/notebooks/{nb_id}")
def rename_notebook(nb_id: int, req: NameUpdate):
    db = SessionLocal()
    nb = db.query(Notebook).filter(Notebook.id == nb_id).first()
    if nb:
        nb.name = req.name
        db.commit()
    db.close()
    return {"message": "Notebook renamed"}

@router.get("/notebooks/{nb_id}/history")
def get_chat_history(nb_id: int):
    db = SessionLocal()
    history = db.query(ChatHistory).filter(ChatHistory.notebook_id == nb_id).order_by(ChatHistory.created_at).all()
    res = [{"role": h.role, "text": h.text} for h in history]
    db.close()
    return {"history": res}

@router.post("/upload")
async def upload_pdf(notebook_id: int, file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    process_pdf(file_path, file.filename) # Note: we'd ideally pass notebook_id to process_pdf to link Document
    
    # Link to Notebook in DB
    db = SessionLocal()
    doc = db.query(Document).filter(Document.filename == file.filename).order_by(Document.id.desc()).first()
    if doc:
        doc.notebook_id = notebook_id
        db.commit()
    db.close()
    
    return {"message": "File uploaded and processed successfully", "filename": file.filename}

class QueryRequest(BaseModel):
    query: str
    sources: Optional[List[int]] = None
    notebook_id: Optional[int] = None

@router.post("/query")
async def query_tutor(request: QueryRequest):
    query = request.query
    sources = request.sources
    
    db = SessionLocal()
    if request.notebook_id:
        # Save user message
        db.add(ChatHistory(notebook_id=request.notebook_id, role="user", text=query))
        db.commit()
    
    stop_words = {"what", "is", "the", "a", "an", "of", "in", "to", "for", "and", "about", "tell", "me", "how"}
    query_terms = [t for t in query.lower().split() if t not in stop_words and len(t) > 2]
    
    matched_concept = None
    concepts_query = db.query(Concept)
    if sources:
        concepts_query = concepts_query.filter(Concept.document_id.in_(sources))
    elif request.notebook_id:
        docs = db.query(Document).filter(Document.notebook_id == request.notebook_id).all()
        doc_ids = [d.id for d in docs]
        concepts_query = concepts_query.filter(Concept.document_id.in_(doc_ids))
        
    concepts = concepts_query.all()
    
    best_match_score = 0
    for c in concepts:
        score = sum(1 for term in query_terms if term in c.name.lower())
        if score > best_match_score:
            best_match_score = score
            matched_concept = c
            
    context = ""
    citations = []
    
    if matched_concept:
        context += f"Verified Concept: {matched_concept.name}\nFact/Definition: {matched_concept.definition}\n\n"
        citations.append(f"Document Graph (Page {matched_concept.page_number})")
        
    where_clause = None
    if sources:
        docs = db.query(Document).filter(Document.id.in_(sources)).all()
        filenames = [d.filename for d in docs]
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
        resp_text = "I do not have enough verified context in my knowledge base to answer this securely."
        if request.notebook_id:
            db.add(ChatHistory(notebook_id=request.notebook_id, role="bot", text=resp_text))
            db.commit()
        db.close()
        return {"response": resp_text}
        
    citation_str = " & ".join(citations)

    # Get recent history context
    history_context = ""
    if request.notebook_id:
        recent = db.query(ChatHistory).filter(ChatHistory.notebook_id == request.notebook_id).order_by(ChatHistory.created_at.desc()).limit(5).all()
        history_context = "\n".join([f"{h.role}: {h.text}" for h in reversed(recent)])

    prompt = f"""
    You are MindVault, an AI Tutor. Answer the user's question using ONLY the provided context below.
    If the context does not contain the answer, explicitly state that you don't know based on the provided documents.
    
    Previous Chat Context:
    {history_context}
    
    Source Material Context:
    {context}
    
    Question: {query}
    """
    
    try:
        response = call_llm(prompt, max_tokens=800)
        answer = response.choices[0].message.content.strip()
        final_ans = f"{answer}\n\n[Source: {citation_str}]"
        
        if request.notebook_id:
            db.add(ChatHistory(notebook_id=request.notebook_id, role="bot", text=final_ans))
            db.commit()
            
        db.close()
        return {"response": final_ans}
    except Exception as e:
        db.close()
        return {"response": f"Error synthesizing answer: {e}"}

@router.get("/sources")
def get_sources(notebook_id: Optional[int] = None):
    db = SessionLocal()
    q = db.query(Document)
    if notebook_id:
        q = q.filter(Document.notebook_id == notebook_id)
    docs = q.all()
    sources = [{"id": d.id, "filename": d.filename} for d in docs]
    db.close()
    return {"sources": sources}

@router.delete("/sources/{doc_id}")
def delete_source(doc_id: int):
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        try:
            res = collection.get(where={"filename": doc.filename})
            if res and res["ids"]:
                collection.delete(ids=res["ids"])
        except Exception:
            pass
        db.delete(doc)
        db.commit()
    db.close()
    return {"message": "Source deleted"}

@router.put("/sources/{doc_id}")
def rename_source(doc_id: int, req: NameUpdate):
    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        old_filename = doc.filename
        doc.filename = req.name
        db.commit()
        # Update Chroma metadata
        try:
            res = collection.get(where={"filename": old_filename})
            if res and res["ids"]:
                new_metadatas = []
                for m in res["metadatas"]:
                    m["filename"] = req.name
                    new_metadatas.append(m)
                collection.update(ids=res["ids"], metadatas=new_metadatas)
        except Exception:
            pass
    db.close()
    return {"message": "Source renamed"}

class ActionRequest(BaseModel):
    action_type: str
    sources: Optional[List[int]] = None
    notebook_id: Optional[int] = None

@router.post("/action")
async def predefined_action(request: ActionRequest):
    db = SessionLocal()
    concepts_query = db.query(Concept)
    if request.sources:
        concepts_query = concepts_query.filter(Concept.document_id.in_(request.sources))
    elif request.notebook_id:
        docs = db.query(Document).filter(Document.notebook_id == request.notebook_id).all()
        doc_ids = [d.id for d in docs]
        concepts_query = concepts_query.filter(Concept.document_id.in_(doc_ids))
        
    concepts = concepts_query.all()
    
    if not concepts:
        db.close()
        return {"response": "No concepts available for this action. Please upload and select a document."}

    context = "\n".join([f"- {c.name}: {c.definition}" for c in concepts])
    
    if request.action_type == "report":
        task = "Write a highly detailed, extremely comprehensive summary report based on the following concepts. Expand significantly on every point, providing examples and deep analysis where possible. The report should be lengthy and informative."
    elif request.action_type == "quiz":
        task = "Generate a comprehensive 10-question multiple choice quiz based on the following concepts. Make the questions challenging. Include a detailed answer key at the bottom with explanations."
    elif request.action_type == "keywords":
        task = "List all the key terms and provide a detailed, paragraph-long explanation for each based on the context."
    elif request.action_type == "subjective":
        task = "Generate exactly 5 complex, subjective essay-style questions based on the following concepts. These questions should test deep conceptual understanding. DO NOT provide any answers."
    else:
        db.close()
        return {"response": "Unknown action type"}
        
    prompt = f"""
    You are MindVault, an expert AI assistant.
    Task: {task}
    
    Context:
    {context}
    """
    
    try:
        response = call_llm(prompt, max_tokens=2500)
        ans = response.choices[0].message.content.strip()
        if request.notebook_id:
            db.add(ChatHistory(notebook_id=request.notebook_id, role="bot", text=ans))
            db.commit()
        db.close()
        return {"response": ans}
    except Exception as e:
        db.close()
        return {"response": f"Error performing action: {e}"}

# --- DIARY ENDPOINTS ---

class DiaryRequest(BaseModel):
    text: str

@router.post("/diary/add")
async def add_diary_entry(req: DiaryRequest):
    # 1. Generate Companion Response
    prompt_companion = f"""
    You are an empathetic, insightful Diary Companion. The user is writing a journal entry.
    Respond with supportive, thought-provoking feedback (2-3 sentences max). Ask a reflective question if appropriate.
    User's entry: {req.text}
    """
    try:
        resp = call_llm(prompt_companion, max_tokens=150)
        companion_text = resp.choices[0].message.content.strip()
    except Exception:
        companion_text = "I'm here for you. Thank you for sharing."
        
    # 2. Synthesize/Summarize entry
    prompt_synth = f"""
    Summarize the core theme or emotion of the following journal entry in one concise sentence.
    Entry: {req.text}
    """
    try:
        resp2 = call_llm(prompt_synth, max_tokens=50)
        synth_text = resp2.choices[0].message.content.strip()
    except Exception:
        synth_text = "A reflective journal entry."
        
    db = SessionLocal()
    entry = DiaryEntry(raw_text=req.text, synthesized_text=synth_text, response_text=companion_text)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    db.close()
    
    return {"companion_response": companion_text, "synthesized_text": synth_text}

@router.get("/diary/history")
def get_diary_history():
    db = SessionLocal()
    entries = db.query(DiaryEntry).order_by(DiaryEntry.created_at).all()
    res = [{"id": e.id, "raw_text": e.raw_text, "response_text": e.response_text, "synthesized_text": e.synthesized_text, "created_at": e.created_at.isoformat()} for e in entries]
    db.close()
    return {"entries": res}

def safe_text(text: str) -> str:
    if not text: return ""
    return str(text).encode('latin-1', 'replace').decode('latin-1')

@router.get("/diary/export")
def export_diary():
    db = SessionLocal()
    entries = db.query(DiaryEntry).order_by(DiaryEntry.created_at).all()
    db.close()
    
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "My Personal Diary", ln=True, align="C")
    pdf.ln(10)
    
    current_date = None
    
    for e in entries:
        date_str = e.created_at.strftime('%A, %B %d, %Y')
        time_str = e.created_at.strftime('%I:%M %p')
        
        # New Date Header
        if date_str != current_date:
            current_date = date_str
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_fill_color(240, 240, 250)
            pdf.cell(0, 10, date_str, ln=True, fill=True)
            pdf.ln(5)
        
        # Entry Time and Theme
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(0, 6, safe_text(f"[{time_str}] Theme: {e.synthesized_text}"))
        
        # User Message
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, safe_text(f"You: {e.raw_text}"))
        
        # AI Response
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(50, 50, 150)
        pdf.multi_cell(0, 6, safe_text(f"MindVault: {e.response_text}"))
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        
    export_path = os.path.join(UPLOAD_DIR, "Diary_Export.pdf")
    pdf.output(export_path)
    
    return FileResponse(path=export_path, filename="Diary_Export.pdf", media_type="application/pdf")

@router.post("/clear")
def clear_databases():
    # Leaving for backward compatibility / testing
    db = SessionLocal()
    try:
        db.query(Concept).delete()
        db.query(Document).delete()
        db.query(ChatHistory).delete()
        db.query(Notebook).delete()
        db.query(DiaryEntry).delete()
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
