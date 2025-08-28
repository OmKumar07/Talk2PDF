import os, sys, json
import pdfplumber
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# -------------------------------
# CONFIG
# -------------------------------
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
STORAGE_DIR = "storage"

# Load embedding model once
embedder = SentenceTransformer(EMBED_MODEL)

# -------------------------------
# PDF INGESTION
# -------------------------------
def extract_pages(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"❌ PDF not found: {pdf_path}")
    
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, p in enumerate(pdf.pages, start=1):
            text = p.extract_text() or ""
            pages.append({"page": i, "text": text})
    return pages

def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def ingest_document(doc_id, pdf_path, out_dir=STORAGE_DIR):
    os.makedirs(out_dir, exist_ok=True)
    pages = extract_pages(pdf_path)
    chunks = []

    for p in pages:
        page_chunks = chunk_text(p["text"])
        for c in page_chunks:
            chunks.append({"page": p["page"], "text": c})

    texts = [c["text"] for c in chunks if c["text"].strip()]
    embeddings = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=True)

    # normalize for cosine similarity with IndexFlatIP
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / (norms + 1e-10)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    idx_path = os.path.join(out_dir, f"{doc_id}.index")
    faiss.write_index(index, idx_path)

    # save chunks metadata
    meta_path = os.path.join(out_dir, f"{doc_id}_chunks.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    return {
        "doc_id": doc_id,
        "pdf_path": pdf_path,
        "num_chunks": len(chunks),
        "index_path": idx_path,
        "meta_path": meta_path
    }

# -------------------------------
# QUERY FUNCTION
# -------------------------------
def load_index(doc_id, out_dir=STORAGE_DIR):
    idx_path = os.path.join(out_dir, f"{doc_id}.index")
    meta_path = os.path.join(out_dir, f"{doc_id}_chunks.json")

    index = faiss.read_index(idx_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    return index, chunks

def search_query(query, doc_id, top_k=3):
    index, chunks = load_index(doc_id)
    q_emb = embedder.encode([query], convert_to_numpy=True)

    # normalize
    q_emb = q_emb / (np.linalg.norm(q_emb, axis=1, keepdims=True) + 1e-10)

    scores, idxs = index.search(q_emb, top_k)

    results = []
    for score, idx in zip(scores[0], idxs[0]):
        results.append({
            "page": chunks[idx]["page"],
            "text": chunks[idx]["text"],
            "score": float(score)
        })
    return results

# -------------------------------
# DEMO / CLI
# -------------------------------
if __name__ == "__main__":
    # ✅ Use command line arg OR fallback to default
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(BASE_DIR, "docs", "sample.pdf")  # default

    doc_id = os.path.splitext(os.path.basename(pdf_path))[0]  # file name as doc_id

    # STEP 1: Ingest PDF
    info = ingest_document(doc_id, pdf_path)
    print("✅ Document Ingested:", info)

    # STEP 2: Ask a query
    query = "What is the main topic of this PDF?"
    results = search_query(query, doc_id)
    print("\n🔎 Query:", query)
    for r in results:
        print(f"\n[Page {r['page']}] (Score {r['score']:.3f})\n{r['text'][:300]}...")
