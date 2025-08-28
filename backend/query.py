import faiss
import json
import numpy as np
from transformers import pipeline
from sentence_transformers import SentenceTransformer

# Load embedding model
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
qa = pipeline("question-answering", model="deepset/roberta-base-squad2", tokenizer="deepset/roberta-base-squad2")

def answer_query(doc_id, question, top_k=4, threshold=0.25):
    # load index
    index = faiss.read_index(f"storage/{doc_id}.index")
    with open(f"storage/{doc_id}_chunks.json","r",encoding="utf8") as f:
        chunks = json.load(f)

    q_emb = embedder.encode([question], convert_to_numpy=True)
    q_emb = q_emb / (np.linalg.norm(q_emb)+1e-10)
    D, I = index.search(q_emb, k=top_k)
    scores = D[0]
    idxs = I[0]

    # filter by threshold
    hits = [(chunks[i], float(scores[j])) for j,i in enumerate(idxs) if scores[j] >= threshold]
    if not hits:
        return {"answer": None, "reason": "No relevant text found in the PDF."}

    # build context by joining top hits (limit length)
    context = "\n\n".join([h[0]["text"] for h in hits])
    res = qa(question=question, context=context)
    # include sources (pages)
    source_pages = list({h[0]["page"] for h in hits})
    return {"answer": res["answer"], "score": float(res["score"]), "sources": source_pages}
