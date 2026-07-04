import chromadb
import os

CHROMA_DIR = "chroma_db"
os.makedirs(CHROMA_DIR, exist_ok=True)

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=CHROMA_DIR)

# Get or create collection
collection = client.get_or_create_collection(name="eduguard_chunks")

def add_chunks_to_vector_db(filename: str, chunks: list[str], metadatas: list[dict], ids: list[str]):
    """Adds document chunks to ChromaDB."""
    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )

def search_vector_db(query: str, n_results: int = 3):
    """Searches the vector database for the query."""
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    return results
