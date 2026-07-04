import PyPDF2
import os
import re
from litellm import completion
from app.database.models import SessionLocal, Document, Concept
from app.database.vector import add_chunks_to_vector_db
from app.config import settings

def extract_concepts_from_text(text_chunk: str) -> list[dict]:
    """Uses Local LLM to extract hierarchical concepts from a chunk of text."""
    prompt = f"""
    Extract the 2 most important specific entities, facts, or concepts from the following text.
    CRITICAL: The definition MUST contain the actual specific details, facts, or data from the text itself, NOT a generic dictionary definition.
    Format your response EXACTLY as a list of concept-definition pairs, separated by pipes. Do not include any other text.
    Format: Entity/Concept Name | Detailed factual explanation based on the text
    
    Excerpt:
    {text_chunk[:2000]}
    """
    
    try:
        api_base = settings.CLOUD_LLM_ENDPOINT if settings.CLOUD_LLM_ENDPOINT else settings.LOCAL_LLM_ENDPOINT
        response = completion(
            model="ollama/llama3.1",
            api_base=api_base,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )
        output = response.choices[0].message.content.strip()
        
        concepts = []
        for line in output.split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    concepts.append({
                        "name": parts[0].strip(),
                        "definition": parts[1].strip()
                    })
        return concepts
    except Exception as e:
        print(f"Extraction error: {e}")
        return []

def process_pdf(filepath: str, filename: str):
    """Parses a PDF, chunks it, extracts concepts, and saves to both databases."""
    db = SessionLocal()
    
    # 1. Create Document in SQLite
    doc = Document(filename=filename)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # 2. Parse PDF
    reader = PyPDF2.PdfReader(filepath)
    
    chunks = []
    metadatas = []
    ids = []
    
    print(f"Processing pages from {filename}...")
    
    # We process up to 20 pages for better coverage
    num_pages_to_process = min(len(reader.pages), 20)
    
    for i in range(num_pages_to_process):
        page = reader.pages[i]
        text = page.extract_text()
        if not text.strip():
            continue
            
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into smaller chunks with overlap
        words = text.split()
        chunk_size = 400
        for j in range(0, len(words), chunk_size - 50):
            chunk_text = ' '.join(words[j:j+chunk_size])
            if len(chunk_text) < 50:
                continue
            
            chunk_id = f"{filename}_p{i+1}_c{j//(chunk_size - 50)}"
            
            chunks.append(chunk_text)
            metadatas.append({"filename": filename, "page": i + 1})
            ids.append(chunk_id)
            
            # Extract Concepts using Local LLM
            extracted_concepts = extract_concepts_from_text(chunk_text)
            for c in extracted_concepts:
                concept_entry = Concept(
                    name=c["name"],
                    definition=c["definition"],
                    page_number=i + 1,
                    document_id=doc.id
                )
                db.add(concept_entry)
            
            # Commit after each page chunk
            db.commit()
            
    # 3. Add to ChromaDB
    if chunks:
        add_chunks_to_vector_db(filename, chunks, metadatas, ids)
        
    db.close()
    print(f"Finished processing {filename}!")
