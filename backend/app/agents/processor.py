import PyPDF2
import os
import re
from litellm import completion
from app.database.models import SessionLocal, Document, Concept
from app.database.vector import add_chunks_to_vector_db

OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

def extract_concepts_from_text(text_chunk: str) -> list[dict]:
    """Uses Local LLM to extract hierarchical concepts from a chunk of text."""
    prompt = f"""
    Extract the 2 most important educational concepts from the following textbook excerpt.
    Format your response EXACTLY as a list of concept-definition pairs, separated by pipes. Do not include any other text.
    Format: Concept Name | A clear, factual definition
    
    Excerpt:
    {text_chunk[:1500]}
    """
    
    try:
        response = completion(
            model="ollama/llama3.1",
            api_base=OLLAMA_API_BASE,
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
    
    print(f"Processing {len(reader.pages)} pages from {filename}...")
    
    # We process just the first 5 pages for demo speed to prevent extremely long extraction times
    num_pages_to_process = min(len(reader.pages), 5)
    
    for i in range(num_pages_to_process):
        page = reader.pages[i]
        text = page.extract_text()
        if not text.strip():
            continue
            
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into smaller chunks (naive chunking for now)
        words = text.split()
        chunk_size = 200
        for j in range(0, len(words), chunk_size):
            chunk_text = ' '.join(words[j:j+chunk_size])
            chunk_id = f"{filename}_p{i+1}_c{j//chunk_size}"
            
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
