# Local-NotebookLM (EduGuard Auto-Tutor)

A privacy-first, anti-hallucination AI tutor designed to digest educational PDFs and provide reliable, grounded answers. Built as a Kaggle Capstone Project.

## Architecture
- **Frontend**: React + Vite (Modern, premium aesthetics with glassmorphism UI)
- **Backend**: FastAPI (Python)
- **AI Core**: Multi-agent system utilizing Local LLMs (for privacy and data parsing) and Cloud LLMs (for complex reasoning).
- **Databases**: ChromaDB (Vector Search) + SQLite (Relational Concept Mapping for strict anti-hallucination).

## Setup Instructions

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

### 3. Environment Variables
Create a `.env` file in the `backend` directory:
```env
OLLAMA_API_BASE=https://twelve-tables-hug.loca.lt
```

## Running the Application
**Terminal 1 (Backend):**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```
