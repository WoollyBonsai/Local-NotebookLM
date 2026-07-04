# MindVault AI

**MindVault** is a privacy-first, locally-hosted AI workspace that seamlessly combines intelligent document analysis with a highly secure personal journaling companion. Built for professionals, researchers, and individuals who demand absolute data sovereignty, MindVault allows you to upload and chat with your sensitive documents completely offline. 

Its unique dual-LLM smart routing system automatically relies on your local models (via Ollama) to guarantee privacy, while intelligently falling back to cloud models (like Kaggle GPUs via Ngrok) only when explicitly configured or when extra compute is required.

## 🚀 Installation & Setup

### 1. Prerequisites
- **Node.js** (v18+) for the frontend
- **Python 3.10+** for the backend
- **Ollama** installed on your system (Download at [ollama.com](https://ollama.com/))

### 2. Setup the LLM Backend (Ollama)
MindVault requires a running Ollama server to act as its brain.
1. Install Ollama from their official website.
2. Pull the necessary models (we recommend `llama3.1`):
   ```bash
   ollama pull llama3.1
   ```
3. Ensure the Ollama server is running (it usually starts automatically, or run `ollama serve`). The default local endpoint will be `http://localhost:11434`.

### 3. Setup the Application Backend
The backend manages the database, document embeddings, and API routes.
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Setup the Application Frontend
The frontend is a Vite + React application.
```bash
cd frontend
npm install
npm run dev
```
Open your browser to `http://localhost:3000`.

---

## ☁️ Setting Up the Cloud Fallback (Kaggle)
If your local computer doesn't have a powerful GPU, MindVault is designed to securely route requests to a cloud GPU (like a free Kaggle notebook) while keeping your documents local.

1. Go to [Kaggle](https://www.kaggle.com/) and create a new Notebook with a GPU (P100 or T4x2).
2. Upload the included `MindVault_Kaggle_Backend.ipynb` file into Kaggle.
3. Add your free Ngrok Auth Token to the final cell.
4. Run all cells in the notebook.
5. The final cell will output a public Ngrok URL (e.g., `https://8a7b-34...ngrok-free.app`).
6. Copy that URL and paste it into the **"Cloud Endpoint"** settings box in the top-right corner of the MindVault UI.

MindVault will now intelligently route complex AI generation tasks to your powerful Kaggle backend!

---

## 🎨 Features
- **Smart Dual-LLM Routing**: Automatically falls back to Cloud API if the Local API goes offline.
- **AI Diary Companion**: Auto-syncing private journal that extracts themes and provides empathetic feedback.
- **PDF Export**: Generate beautiful PDF exports of your personal AI diary.
- **Vector Document Chat**: Chat directly with your PDFs and code files using ChromaDB local embeddings.
- **Subjective Qs & Quizzes**: Instantly generate 10-question quizzes or essay topics to test your knowledge of your documents.

## 🤝 Contributing
MindVault is built for maximum data sovereignty. Feel free to fork and customize the prompts, aesthetics, and embedding models!
