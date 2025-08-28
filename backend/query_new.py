import faiss
import json
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
import torch
import re

# Load better models for improved accuracy
embedder = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")  # Better embedding model
qa = pipeline("question-answering",
              model="deepset/deberta-v3-large-squad2",
              tokenizer="deepset/deberta-v3-large-squad2",
              return_all_scores=False,
              handle_impossible_answer=True)

def analyze_question_intent(question):
    """
    Analyze question to understand what type of answer is needed
    """
    question_lower = question.lower()
    
    intent = {
        'requires_definition': False,
        'requires_summary': False,
        'requires_process': False,
        'requires_comparison': False,
        'requires_specific_fact': False,
        'keywords': [],
        'complexity': 'simple'
    }
    
    # Detect question types
    if any(phrase in question_lower for phrase in ['what is', 'define', 'definition of', 'meaning of']):
        intent['requires_definition'] = True
        intent['complexity'] = 'medium'
    
    elif any(phrase in question_lower for phrase in ['summarize', 'overview', 'main points', 'key concepts']):
        intent['requires_summary'] = True
        intent['complexity'] = 'complex'
    
    elif any(phrase in question_lower for phrase in ['how to', 'process', 'steps', 'procedure', 'method']):
        intent['requires_process'] = True
        intent['complexity'] = 'medium'
    
    elif any(phrase in question_lower for phrase in ['compare', 'difference', 'versus', 'vs']):
        intent['requires_comparison'] = True
        intent['complexity'] = 'complex'
    
    else:
        intent['requires_specific_fact'] = True
        intent['complexity'] = 'simple'
    
    # Extract keywords (simple approach)
    words = re.findall(r'\b\w+\b', question_lower)
    stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'to', 'of', 'in', 'for', 'with', 'on', 'at', 'by', 'from', 'as', 'are', 'was', 'were', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
    intent['keywords'] = [word for word in words if word not in stop_words and len(word) > 2]
    
    return intent

def generate_question_variants(question, intent):
    """
    Generate multiple question variants for better retrieval
    """
    variants = [question]
    q_lower = question.lower()
    
    # Add intent-based variants
    if intent['requires_definition']:
        term = extract_main_term(question)
        if term:
            variants.extend([
                f"definition of {term}",
                f"{term} meaning explanation",
                f"what does {term} mean",
                f"{term} concept overview"
            ])
    
    elif intent['requires_summary']:
        variants.extend([
            "main points key concepts",
            "important information overview", 
            "summary of content",
            "key findings conclusions"
        ])
    
    elif intent['requires_process']:
        variants.extend([
            "steps procedure method",
            "how to process approach",
            "methodology implementation",
            "procedure steps guidelines"
        ])
    
    # Add keyword-based variants
    if intent['keywords']:
        keyword_query = " ".join(intent['keywords'][:3])  # Top 3 keywords
        variants.append(keyword_query)
        variants.append(f"information about {keyword_query}")
    
    return variants[:5]  # Limit to 5 variants

def extract_main_term(question):
    """
    Extract the main term being asked about
    """
    q_lower = question.lower()
    if 'what is' in q_lower:
        parts = q_lower.split('what is')
        if len(parts) > 1:
            term = parts[1].strip().rstrip('?').strip()
            return term
    return None

def generate_no_results_response(question, intent):
    """
    Generate helpful response when no results found
    """
    if intent['requires_summary']:
        return {
            "answer": "I couldn't find sufficient content to create a comprehensive summary. The document might not contain the type of overview information you're looking for, or you might need to ask about specific topics covered in the document.",
            "sources": [],
            "score": 0.0
        }
    elif intent['requires_definition']:
        term = extract_main_term(question)
        return {
            "answer": f"I couldn't find a definition for '{term or 'the requested term'}' in this document. The term might not be defined in this PDF, or it might be referred to using different terminology.",
            "sources": [],
            "score": 0.0
        }
    else:
        return {
            "answer": "I couldn't find relevant information about your question in this PDF. Try rephrasing your question, asking about different aspects, or checking if the topic is covered in the document.",
            "sources": [],
            "score": 0.0
        }

def rank_and_deduplicate_hits(all_hits, question, intent):
    """
    Advanced ranking and deduplication of retrieved chunks
    """
    # Group hits by chunk content to avoid duplicates
    unique_hits = {}
    for chunk_data, score, query_variant in all_hits:
        chunk_id = f"{chunk_data['page']}_{hash(chunk_data['text'][:100])}"
        
        if chunk_id not in unique_hits or score > unique_hits[chunk_id][1]:
            unique_hits[chunk_id] = (chunk_data, score, query_variant)
    
    # Convert back to list and sort by score
    hits = list(unique_hits.values())
    hits.sort(key=lambda x: x[1], reverse=True)
    
    # Apply intent-based ranking adjustments
    for i, (chunk_data, score, query_variant) in enumerate(hits):
        adjusted_score = score
        
        # Boost scores for content that matches intent
        text_lower = chunk_data['text'].lower()
        
        if intent['requires_definition'] and any(word in text_lower for word in ['definition', 'means', 'refers to', 'is defined as']):
            adjusted_score *= 1.3
        elif intent['requires_summary'] and any(word in text_lower for word in ['overview', 'summary', 'key', 'main', 'important']):
            adjusted_score *= 1.2
        elif intent['requires_process'] and any(word in text_lower for word in ['step', 'process', 'method', 'procedure']):
            adjusted_score *= 1.3
        
        # Boost for keyword matches
        keyword_matches = sum(1 for kw in intent['keywords'] if kw in text_lower)
        if keyword_matches > 0:
            adjusted_score *= (1 + 0.1 * keyword_matches)
        
        hits[i] = (chunk_data, adjusted_score, query_variant)
    
    # Re-sort with adjusted scores
    hits.sort(key=lambda x: x[1], reverse=True)
    
    return hits[:12]  # Return top 12

def build_intelligent_context(ranked_hits, question, intent, max_length=4000):
    """
    Build context intelligently based on question intent
    """
    context_parts = []
    current_length = 0
    pages_used = set()
    
    # Strategy depends on intent
    if intent['requires_summary']:
        max_per_page = 2
        page_counts = {}
    else:
        max_per_page = 4
        page_counts = {}
    
    for chunk_data, score, query_variant in ranked_hits:
        page_num = chunk_data['page']
        text = chunk_data['text'].strip()
        
        # Skip if we have too much from this page
        if page_counts.get(page_num, 0) >= max_per_page:
            continue
        
        # Clean and prepare text
        cleaned_text = clean_and_enhance_text(text, intent)
        
        # Add page and score context
        context_chunk = f"[Page {page_num}, Relevance: {score:.2f}]\n{cleaned_text}"
        
        # Check length constraints
        if current_length + len(context_chunk) > max_length:
            remaining = max_length - current_length - 100
            if remaining > 200:
                truncated = context_chunk[:remaining] + "..."
                context_parts.append(truncated)
            break
        
        context_parts.append(context_chunk)
        current_length += len(context_chunk)
        page_counts[page_num] = page_counts.get(page_num, 0) + 1
        pages_used.add(page_num)
    
    return "\n\n".join(context_parts)

def clean_and_enhance_text(text, intent):
    """
    Clean and enhance text based on intent
    """
    # Basic cleaning
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove obvious headers/footers
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if (len(line) > 5 and 
            not line.isdigit() and 
            not line.startswith(('Page ', 'Chapter ', 'Section '))):
            cleaned_lines.append(line)
    
    cleaned_text = ' '.join(cleaned_lines)
    
    return cleaned_text

def generate_insufficient_context_response(question, ranked_hits):
    """
    Handle cases where context is too short
    """
    pages = list({h[0]["page"] for h in ranked_hits})
    return {
        "answer": f"I found some relevant content on page(s) {', '.join(map(str, pages))}, but it's too brief to provide a comprehensive answer. Please try asking a more specific question about the content on these pages.",
        "sources": pages,
        "score": 0.2
    }

def generate_answer_with_strategy(question, context, strategy, intent):
    """
    Generate answers using different strategies
    """
    try:
        if strategy == 'direct':
            res = qa(question=question, context=context)
            return res["answer"] if res["score"] > 0.3 else None
        
        elif strategy == 'contextual':
            contextual_question = f"Based on the document, {question.lower()}"
            res = qa(question=contextual_question, context=context)
            return res["answer"] if res["score"] > 0.25 else None
        
        elif strategy == 'extractive':
            # Find most relevant sentences
            sentences = context.split('.')
            relevant_sentences = []
            for sentence in sentences:
                if any(kw in sentence.lower() for kw in intent['keywords'][:3]):
                    relevant_sentences.append(sentence.strip())
            
            if relevant_sentences:
                mini_context = '. '.join(relevant_sentences[:3])
                res = qa(question=question, context=mini_context)
                return res["answer"] if res["score"] > 0.2 else None
        
    except Exception:
        return None
    
    return None

def generate_custom_answer(question, context, ranked_hits, intent):
    """
    Generate custom answers using our enhanced logic
    """
    if intent['requires_summary']:
        return create_comprehensive_summary(ranked_hits)
    elif intent['requires_definition']:
        return create_definition_answer(ranked_hits, question)
    elif intent['requires_process']:
        return create_process_answer(ranked_hits)
    else:
        return create_summary_answer(question, context, ranked_hits)

def create_comprehensive_summary(ranked_hits):
    """Create a comprehensive summary from multiple chunks"""
    key_points = []
    pages_covered = set()
    
    for chunk_data, score, _ in ranked_hits[:6]:
        text = chunk_data['text']
        page = chunk_data['page']
        
        # Extract key sentences
        sentences = text.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if (len(sentence) > 30 and 
                any(keyword in sentence.lower() for keyword in ['important', 'key', 'main', 'significant', 'conclude'])):
                if sentence not in key_points:
                    key_points.append(sentence)
                    pages_covered.add(page)
        
        if len(key_points) >= 5:
            break
    
    if key_points:
        summary = ". ".join(key_points[:4]) + "."
        return f"{summary} (Information compiled from pages: {', '.join(map(str, sorted(pages_covered)))})"
    
    return None

def create_definition_answer(ranked_hits, question):
    """Create definition-focused answer"""
    term = extract_main_term(question)
    definition_text = []
    
    for chunk_data, score, _ in ranked_hits[:3]:
        text = chunk_data['text'].lower()
        if term and any(pattern in text for pattern in [f"{term} is", f"{term} refers", f"{term} means"]):
            definition_text.append(chunk_data['text'])
    
    if definition_text:
        return f"Based on the document: {definition_text[0][:200]}..."
    
    return None

def create_process_answer(ranked_hits):
    """Create process/procedure focused answer"""
    process_steps = []
    
    for chunk_data, score, _ in ranked_hits[:4]:
        text = chunk_data['text']
        if any(word in text.lower() for word in ['step', 'first', 'second', 'then', 'next', 'finally']):
            process_steps.append(text)
    
    if process_steps:
        return f"Process information: {' '.join(process_steps[:2])}"
    
    return None

def create_summary_answer(question, context, ranked_hits):
    """Create a summary-style answer"""
    # Extract most relevant sentence from top hit
    if ranked_hits:
        top_chunk = ranked_hits[0][0]['text']
        sentences = top_chunk.split('.')
        best_sentence = max(sentences, key=len) if sentences else top_chunk
        return best_sentence.strip()
    
    return None

def generate_fallback_response(question, ranked_hits, intent):
    """
    Generate fallback response when all else fails
    """
    pages = sorted(list({h[0]["page"] for h in ranked_hits}))
    
    if intent['requires_summary']:
        answer = "I found relevant content but couldn't generate a comprehensive summary. Key information appears on pages: " + ", ".join(map(str, pages))
    elif intent['requires_definition']:
        term = extract_main_term(question)
        answer = f"I found some references to '{term or 'the topic'}' on pages {', '.join(map(str, pages))}, but couldn't extract a clear definition."
    else:
        answer = f"I found potentially relevant information on pages {', '.join(map(str, pages))}, but couldn't generate a confident answer. Please try asking about specific aspects mentioned on these pages."
    
    return {
        "answer": answer,
        "sources": pages,
        "score": 0.3
    }

def select_best_answer(answer_candidates, question, intent):
    """
    Select the best answer from multiple candidates
    """
    if not answer_candidates:
        return "No suitable answer could be generated."
    
    # Score each candidate
    scored_answers = []
    for answer in answer_candidates:
        score = 0
        
        # Length score (prefer reasonable length)
        length = len(answer)
        if 50 <= length <= 500:
            score += 20
        elif 20 <= length <= 50:
            score += 10
        elif length > 500:
            score += 15
        
        # Keyword presence
        for keyword in intent['keywords']:
            if keyword in answer.lower():
                score += 5
        
        # Structure score
        if answer.startswith(('Based on', 'According to', 'The document')):
            score += 5
        if '(Page' in answer:
            score += 3
        
        scored_answers.append((answer, score))
    
    # Return best scored answer
    scored_answers.sort(key=lambda x: x[1], reverse=True)
    return scored_answers[0][0]

def calculate_answer_confidence(answer, context, ranked_hits):
    """
    Calculate confidence score for the answer
    """
    if not answer or len(answer) < 10:
        return 0.0
    
    confidence = 0.4  # Base confidence
    
    # Length factor
    if 30 <= len(answer) <= 300:
        confidence += 0.2
    elif len(answer) > 300:
        confidence += 0.1
    
    # Source diversity
    unique_pages = len(set(h[0]["page"] for h in ranked_hits[:5]))
    confidence += min(0.2, unique_pages * 0.05)
    
    # Context relevance (how much of context seems relevant)
    if len(context) > 1000:
        confidence += 0.1
    
    return min(confidence, 0.95)  # Cap at 95%

def enhance_answer_quality(answer, question, intent, ranked_hits):
    """
    Final enhancement of answer quality
    """
    if not answer:
        return answer
    
    # Add page references if missing and available
    if '(Page' not in answer and ranked_hits:
        pages = sorted(list({h[0]["page"] for h in ranked_hits[:3]}))
        if len(pages) <= 3:
            answer += f" (Referenced from pages: {', '.join(map(str, pages))})"
    
    # Ensure proper capitalization
    if answer and not answer[0].isupper():
        answer = answer[0].upper() + answer[1:]
    
    # Ensure proper ending
    if answer and not answer.strip().endswith(('.', '!', '?', ':')):
        answer = answer.strip() + '.'
    
    return answer

def answer_query(doc_id, question, top_k=8, threshold=0.3):
    """
    Advanced multi-stage query processing for significantly improved accuracy
    """
    try:
        # Step 1: Analyze question intent and complexity
        question_analysis = analyze_question_intent(question)
        
        # Step 2: Generate multiple question variants for better retrieval coverage
        processed_questions = generate_question_variants(question, question_analysis)
        
        # Step 3: Load document embeddings and chunks
        index = faiss.read_index(f"storage/{doc_id}.index")
        with open(f"storage/{doc_id}_chunks.json", "r", encoding="utf-8") as f:
            chunks = json.load(f)
        
        # Step 4: Multi-query retrieval with different strategies
        all_hits = []
        for variant_question in processed_questions:
            query_embedding = embedder.encode([variant_question])
            query_embedding = query_embedding.astype('float32')
            
            # Search with dynamic top_k based on question complexity
            search_k = top_k * 2 if question_analysis['complexity'] == 'complex' else top_k
            scores, indices = index.search(query_embedding, min(search_k, len(chunks)))
            
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and score >= threshold:
                    chunk_data = chunks[idx]
                    all_hits.append((chunk_data, float(score), variant_question))
        
        # Step 5: Handle no results case
        if not all_hits:
            return generate_no_results_response(question, question_analysis)
        
        # Step 6: Advanced ranking and deduplication
        ranked_hits = rank_and_deduplicate_hits(all_hits, question, question_analysis)
        
        # Step 7: Build intelligent context based on intent
        context = build_intelligent_context(ranked_hits, question, question_analysis, max_length=4000)
        
        if len(context) < 100:
            return generate_insufficient_context_response(question, ranked_hits)
        
        # Step 8: Multi-strategy answer generation
        answer_candidates = []
        
        # Try different answering strategies
        for strategy in ['direct', 'contextual', 'extractive']:
            candidate = generate_answer_with_strategy(question, context, strategy, question_analysis)
            if candidate and len(candidate) > 10:
                answer_candidates.append(candidate)
        
        # Step 9: Generate custom answers using our enhanced logic
        try:
            custom_answer = generate_custom_answer(question, context, ranked_hits, question_analysis)
            if custom_answer:
                answer_candidates.append(custom_answer)
        except Exception:
            pass
        
        # Step 10: Fallback if no good answers generated
        if not answer_candidates:
            return generate_fallback_response(question, ranked_hits, question_analysis)
        
        # Step 11: Select and refine the best answer
        best_answer = select_best_answer(answer_candidates, question, question_analysis)
        confidence = calculate_answer_confidence(best_answer, context, ranked_hits)
        
        # Step 12: Final answer enhancement
        final_answer = enhance_answer_quality(best_answer, question, question_analysis, ranked_hits)
        
        # Step 13: Compile comprehensive response
        sources = list(set(chunk["page"] for chunk, _, _ in ranked_hits[:5]))
        
        return {
            "answer": final_answer,
            "sources": sorted(sources),
            "score": confidence
        }
        
    except Exception as e:
        return {
            "answer": f"I encountered an error while processing your question: {str(e)}. Please try rephrasing your question or check if the document was uploaded correctly.",
            "sources": [],
            "score": 0.0
        }

# Alternative function for complex queries that need more context and different processing
def answer_complex_query(doc_id, question, top_k=12, threshold=0.1):
    """
    For complex questions that might need more context and different processing
    """
    return answer_query(doc_id, question, top_k=top_k, threshold=threshold)
