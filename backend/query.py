import faiss
import json
import numpy as np
from transformers import pipeline
from sentence_transformers import SentenceTransformer

# Load embedding model
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
qa = pipeline("question-answering", model="deepset/roberta-base-squad2", tokenizer="deepset/roberta-base-squad2")

def answer_query(doc_id, question, top_k=8, threshold=0.15):
    """
    Enhanced query system with better context building and answer generation
    """
    try:
        # Preprocess question for better matching
        processed_question = preprocess_question(question)
        
        # Load index and chunks
        index = faiss.read_index(f"storage/{doc_id}.index")
        with open(f"storage/{doc_id}_chunks.json","r",encoding="utf8") as f:
            chunks = json.load(f)

        # Encode and normalize query
        q_emb = embedder.encode([processed_question], convert_to_numpy=True)
        q_emb = q_emb / (np.linalg.norm(q_emb)+1e-10)
        
        # Search for relevant chunks
        D, I = index.search(q_emb, k=top_k)
        scores = D[0]
        idxs = I[0]

        # Filter by threshold and get hits
        hits = [(chunks[i], float(scores[j])) for j,i in enumerate(idxs) if scores[j] >= threshold]
        
        if not hits:
            return {
                "answer": "I couldn't find relevant information about your question in this PDF. Try rephrasing your question or asking about different topics covered in the document.",
                "reason": "No relevant text found in the PDF.",
                "sources": [],
                "score": 0.0
            }

        # Smart context building
        context = build_smart_context(hits, question, max_length=2000)
        
        # Generate answer using QA pipeline
        if len(context.strip()) < 50:
            return {
                "answer": "The relevant text found is too short to provide a meaningful answer. Please try a more specific question.",
                "sources": list({h[0]["page"] for h in hits}),
                "score": 0.0
            }
        
        # Try to get answer from QA model
        try:
            res = qa(question=question, context=context)
            answer = res["answer"]
            confidence = float(res["score"])
            
            # If confidence is too low, provide a better response
            if confidence < 0.3:
                # Create a summary-style answer from the context
                answer = create_summary_answer(question, context, hits)
                confidence = max(confidence, 0.5)  # Boost confidence for summary answers
                
        except Exception as e:
            print(f"QA pipeline error: {e}")
            answer = create_summary_answer(question, context, hits)
            confidence = 0.6

        # Include sources (pages)
        source_pages = sorted(list({h[0]["page"] for h in hits}))
        
        return {
            "answer": answer,
            "score": confidence,
            "sources": source_pages
        }
        
    except Exception as e:
        print(f"Error in answer_query: {e}")
        return {
            "answer": "Sorry, I encountered an error while processing your question. Please try again.",
            "sources": [],
            "score": 0.0
        }

def preprocess_question(question):
    """
    Enhance question for better semantic matching
    """
    question = question.strip()
    
    # Add context keywords for better matching
    question_lower = question.lower()
    
    # Add relevant keywords based on question type
    if any(word in question_lower for word in ['author', 'authors', 'contributor', 'written by']):
        question += " author contributor written by"
    elif any(word in question_lower for word in ['what is', 'define', 'definition']):
        question += " definition meaning explanation"
    elif any(word in question_lower for word in ['how', 'method', 'process']):
        question += " method process procedure steps"
    elif any(word in question_lower for word in ['why', 'reason', 'cause']):
        question += " reason cause explanation rationale"
    
    return question

def build_smart_context(hits, question, max_length=2000):
    """
    Build optimized context by prioritizing relevant chunks and managing length
    """
    # Sort hits by relevance score
    sorted_hits = sorted(hits, key=lambda x: x[1], reverse=True)
    
    context_parts = []
    current_length = 0
    
    for chunk_data, score in sorted_hits:
        chunk_text = chunk_data["text"].strip()
        page_num = chunk_data["page"]
        
        # Add page context for better readability
        chunk_with_context = f"[Page {page_num}] {chunk_text}"
        
        # Check if adding this chunk would exceed max length
        if current_length + len(chunk_with_context) > max_length:
            # Try to add a truncated version
            remaining_space = max_length - current_length - 50  # Leave some buffer
            if remaining_space > 100:  # Only add if meaningful space remains
                truncated = chunk_with_context[:remaining_space] + "..."
                context_parts.append(truncated)
            break
        
        context_parts.append(chunk_with_context)
        current_length += len(chunk_with_context)
    
    return "\n\n".join(context_parts)

def create_summary_answer(question, context, hits):
    """
    Create a better answer when QA model confidence is low
    """
    # Extract key information from context
    context_sentences = []
    for chunk_data, score in hits[:3]:  # Use top 3 chunks
        text = chunk_data["text"].strip()
        page = chunk_data["page"]
        
        # Split into sentences and take most relevant ones
        sentences = text.split('. ')
        for sentence in sentences[:2]:  # Take first 2 sentences from each chunk
            if len(sentence.strip()) > 20:  # Only meaningful sentences
                context_sentences.append(f"{sentence.strip()}. (Page {page})")
    
    if not context_sentences:
        return "Based on the content found, I cannot provide a specific answer to your question."
    
    # Create a more informative response
    if len(context_sentences) == 1:
        return f"Based on the document: {context_sentences[0]}"
    else:
        answer = "Based on the document content:\n\n"
        for i, sentence in enumerate(context_sentences[:3], 1):
            answer += f"{i}. {sentence}\n"
        return answer.strip()

# Alternative function for complex queries that need more context
def answer_complex_query(doc_id, question, top_k=12, threshold=0.1):
    """
    For complex questions that might need more context and different processing
    """
    return answer_query(doc_id, question, top_k=top_k, threshold=threshold)
