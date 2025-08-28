import json
import os
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    print("⚠️  Warning: GEMINI_API_KEY not configured properly")
    print("🔑 Please set your actual Gemini API key in the .env file")
    print("📖 Get your key from: https://makersuite.google.com/app/apikey")
    # Don't configure genai yet - wait until we have a real key
    genai = None
    model = None
else:
    genai.configure(api_key=GEMINI_API_KEY)
    # Initialize Gemini model
    model = genai.GenerativeModel('gemini-1.5-flash')

class LightweightRetriever:
    """Lightweight text retrieval using TF-IDF instead of heavy models"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            max_df=0.95,
            min_df=2
        )
        self.chunks = []
        self.vectors = None
        
    def index_chunks(self, chunks):
        """Index document chunks using TF-IDF"""
        self.chunks = chunks
        if chunks:
            texts = [chunk.get('text', '') for chunk in chunks]
            self.vectors = self.vectorizer.fit_transform(texts)
        
    def search(self, query, top_k=5):
        """Search for relevant chunks using cosine similarity"""
        if not self.chunks or self.vectors is None:
            return []
            
        # Transform query
        query_vector = self.vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.vectors).flatten()
        
        # Get top results
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Minimum similarity threshold
                results.append({
                    'chunk': self.chunks[idx],
                    'similarity': float(similarities[idx])
                })
        
        return results

# Global retriever instance
retriever = LightweightRetriever()

def load_document_chunks(doc_id):
    """Load document chunks for a specific document"""
    chunks_file = f"storage/{doc_id}_chunks.json"
    if os.path.exists(chunks_file):
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
            retriever.index_chunks(chunks)
            return chunks
    return []

def create_gemini_prompt(question, context_chunks):
    """Create a focused prompt for Gemini API"""
    
    # Combine relevant context
    context_text = "\n\n".join([
        f"Section {i+1}: {chunk['text'][:800]}"  # Limit chunk size
        for i, chunk in enumerate(context_chunks[:4])  # Max 4 chunks
    ])
    
    prompt = f"""You are an AI assistant that answers questions STRICTLY based on the provided PDF document content.

IMPORTANT RULES:
1. Answer ONLY using information from the provided context
2. If the answer is not in the context, say "I cannot find this information in the provided document"
3. Be concise and direct - avoid unnecessary elaboration
4. Do not add external knowledge or assumptions
5. Quote specific parts when relevant

DOCUMENT CONTEXT:
{context_text}

QUESTION: {question}

ANSWER (be concise and factual):"""

    return prompt

def answer_query_gemini(doc_id, question):
    """Answer question using Gemini API with PDF content only"""
    
    if not model:
        return {
            "answer": "Gemini API is not configured. Please set your GEMINI_API_KEY in the .env file. Get your key from: https://makersuite.google.com/app/apikey",
            "confidence": 0.0,
            "sources": []
        }
    
    try:
        # Load document chunks
        chunks = load_document_chunks(doc_id)
        if not chunks:
            return {
                "answer": "Document not found or not processed yet.",
                "confidence": 0.0,
                "sources": []
            }
        
        # Search for relevant chunks
        relevant_results = retriever.search(question, top_k=5)
        
        if not relevant_results:
            return {
                "answer": "I cannot find relevant information in the document to answer your question.",
                "confidence": 0.0,
                "sources": []
            }
        
        # Extract chunks with good similarity
        context_chunks = [
            result['chunk'] for result in relevant_results 
            if result['similarity'] > 0.15
        ]
        
        if not context_chunks:
            return {
                "answer": "I cannot find relevant information in the document to answer your question.",
                "confidence": 0.0,
                "sources": []
            }
        
        # Create prompt for Gemini
        prompt = create_gemini_prompt(question, context_chunks)
        
        # Generate response with Gemini
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for factual responses
                    max_output_tokens=300,  # Concise responses
                    top_p=0.8,
                    top_k=40
                )
            )
            
            answer = response.text.strip()
            
            # Calculate confidence based on context relevance
            avg_similarity = np.mean([r['similarity'] for r in relevant_results[:3]])
            confidence = min(avg_similarity * 2, 1.0)  # Scale to 0-1
            
            # Prepare sources
            sources = []
            for i, result in enumerate(relevant_results[:3]):
                chunk = result['chunk']
                sources.append({
                    "page": chunk.get('page', i+1),
                    "text": chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text'],
                    "relevance": round(result['similarity'], 3)
                })
            
            return {
                "answer": answer,
                "confidence": round(confidence, 3),
                "sources": sources
            }
            
        except Exception as e:
            return {
                "answer": f"Error generating response: {str(e)}",
                "confidence": 0.0,
                "sources": []
            }
            
    except Exception as e:
        return {
            "answer": f"Error processing query: {str(e)}",
            "confidence": 0.0,
            "sources": []
        }

def answer_complex_query_gemini(doc_id, question):
    """Handle complex questions with multi-step reasoning using Gemini"""
    
    if not model:
        return {
            "answer": "Gemini API is not configured. Please set your GEMINI_API_KEY in the .env file. Get your key from: https://makersuite.google.com/app/apikey",
            "confidence": 0.0,
            "sources": []
        }
    
    try:
        # Load document chunks
        chunks = load_document_chunks(doc_id)
        if not chunks:
            return {
                "answer": "Document not found or not processed yet.",
                "confidence": 0.0,
                "sources": []
            }
        
        # For complex queries, search with multiple strategies
        search_terms = extract_key_terms(question)
        all_relevant = set()
        
        # Search with original question
        results1 = retriever.search(question, top_k=4)
        all_relevant.update(range(len(results1)))
        
        # Search with key terms
        for term in search_terms[:3]:  # Limit to 3 terms
            results2 = retriever.search(term, top_k=3)
            all_relevant.update(range(len(results2)))
        
        # Combine and rank results
        combined_results = results1[:4] + [r for r in retriever.search(' '.join(search_terms), top_k=3) if r not in results1[:4]]
        
        if not combined_results:
            return {
                "answer": "I cannot find relevant information in the document to answer your question.",
                "confidence": 0.0,
                "sources": []
            }
        
        # Use top chunks for context
        context_chunks = [r['chunk'] for r in combined_results[:5]]
        
        # Enhanced prompt for complex queries
        context_text = "\n\n".join([
            f"Section {i+1}: {chunk['text'][:600]}"
            for i, chunk in enumerate(context_chunks)
        ])
        
        complex_prompt = f"""You are an AI assistant that provides comprehensive answers STRICTLY based on the provided PDF document content.

IMPORTANT RULES:
1. Answer ONLY using information from the provided context
2. For complex questions, synthesize information from multiple sections if available
3. Be concise but thorough - provide complete information without unnecessary elaboration
4. If the complete answer is not in the context, clearly state what information is missing
5. Structure your answer logically (use bullet points if helpful)
6. Do not add external knowledge

DOCUMENT CONTEXT:
{context_text}

COMPLEX QUESTION: {question}

COMPREHENSIVE ANSWER (be thorough but concise):"""

        # Generate response
        response = model.generate_content(
            complex_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,  # Slightly higher for synthesis
                max_output_tokens=500,  # More tokens for complex answers
                top_p=0.9,
                top_k=50
            )
        )
        
        answer = response.text.strip()
        
        # Calculate confidence
        avg_similarity = np.mean([r['similarity'] for r in combined_results[:4]])
        confidence = min(avg_similarity * 1.8, 1.0)
        
        # Prepare sources
        sources = []
        for i, result in enumerate(combined_results[:4]):
            chunk = result['chunk']
            sources.append({
                "page": chunk.get('page', i+1),
                "text": chunk['text'][:250] + "..." if len(chunk['text']) > 250 else chunk['text'],
                "relevance": round(result['similarity'], 3)
            })
        
        return {
            "answer": answer,
            "confidence": round(confidence, 3),
            "sources": sources
        }
        
    except Exception as e:
        return {
            "answer": f"Error processing complex query: {str(e)}",
            "confidence": 0.0,
            "sources": []
        }

def extract_key_terms(question):
    """Extract key terms from question for better search"""
    # Remove common question words
    stop_words = {'what', 'how', 'when', 'where', 'why', 'who', 'which', 'is', 'are', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once'}
    
    # Simple word extraction
    words = re.findall(r'\b\w+\b', question.lower())
    key_terms = [word for word in words if len(word) > 3 and word not in stop_words]
    
    return key_terms[:5]  # Return top 5 terms
