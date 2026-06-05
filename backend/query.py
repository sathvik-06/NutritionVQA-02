import os
import sys
import pickle
import numpy as np

# Add backend dir to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Error: Required libraries missing: {e}. Please run the ingest pipeline first.")
    sys.exit(1)

# Paths
INDEX_DIR = os.path.join(backend_dir, "rag", "faiss_index")
INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")
METADATA_PATH = os.path.join(INDEX_DIR, "metadata.pkl")

def query_vector_store(query_str: str, k: int = 3):
    """Retrieve top k matching documents from the local FAISS store."""
    if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
        print("[ERROR] FAISS index or metadata not found. Please run: python backend/ingest.py first.")
        return

    # Load FAISS index
    print("[FAISS] Loading FAISS index...")
    index = faiss.read_index(INDEX_PATH)

    # Load Metadata
    print("[Metadata] Loading metadata...")
    with open(METADATA_PATH, "rb") as f:
        documents = pickle.load(f)

    # Load Embedding Model
    print("[Model] Loading Sentence-Transformer model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Encode query and normalize for Cosine Similarity (Inner Product)
    query_vector = model.encode([query_str], convert_to_numpy=True)
    norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
    normalized_query = query_vector / (norm + 1e-10)

    # Search FAISS index
    scores, indices = index.search(normalized_query, k)

    print("\n[Query]", query_str)
    print(f"==================================================")
    
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
        if idx == -1 or idx >= len(documents):
            continue
        doc = documents[idx]
        print(f"\n[Rank {rank + 1}] Similarity Score: {score:.4f}")
        print(f"Question: {doc['metadata']['question']}")
        print(f"Answer: {doc['metadata']['answer']}")
        if doc['metadata'].get('additional_context'):
            print(f"Context: {doc['metadata']['additional_context']}")
        print(f"--------------------------------------------------")

def main():
    if len(sys.argv) < 2:
        query_str = input("Enter a nutrition query to search: ")
    else:
        query_str = " ".join(sys.argv[1:])

    if not query_str.strip():
        print("Query string cannot be empty.")
        sys.exit(1)

    query_vector_store(query_str)

if __name__ == "__main__":
    main()
