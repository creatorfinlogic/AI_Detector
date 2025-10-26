

# /ai_detector_pro/analysis.py

import re
import numpy as np
import textstat
from models import calculate_perplexity, calculate_roberta_score

# ==========================================================
# SECTION 1: CONSTANTS AND SUGGESTIONS
# ==========================================================

# --- Analysis Constants ---
AI_PERP_VERY_LOW = 15.0
AI_PERP_LOW = 30.0
HUMAN_PERP_MIN = 50.0
HUMAN_PERP_GOOD = 100.0
LEXICAL_DIVERSITY_MIN = 0.45
LEXICAL_DIVERSITY_GOOD = 0.60
READABILITY_UNIFORMITY_THRESHOLD = 4.0
AI_BOILERPLATE = [r'In conclusion', r'It is imperative', r'Furthermore', r'Moreover', r'Thus', r'Hence']

# --- Suggestions Dictionary ---
SUGGESTIONS = {
    "AI_VERY_PREDICTABLE": {"symbol": "🔴", "short": "Extremely predictable", "suggestion": "This sentence is too generic. Add specific details, personal observations, or sensory language."},
    "AI_PREDICTABLE": {"symbol": "🟠", "short": "Predictable phrasing", "suggestion": "This reads like a template. Break the pattern with a surprising word or a concrete example."},
    "UNIFORM_RHYTHM": {"symbol": "🟡", "short": "Robotic sentence rhythm", "suggestion": "Sentence lengths are too uniform. Vary the structure by combining short and long sentences."},
    "BOILERPLATE": {"symbol": "🟤", "short": "Generic transition", "suggestion": "This is a common AI transition phrase. Try to make it more conversational or remove it entirely."},
    "LOW_DIVERSITY": {"symbol": "🟣", "short": "Repetitive vocabulary", "suggestion": "Vocabulary is repetitive in this section. Use synonyms or restructure sentences to avoid repeating words."},
    "MIXED": {"symbol": "🟢", "short": "Good variation", "suggestion": "This shows some human-like qualities. Consider adding one more personal touch to enhance authenticity."},
    "HUMAN": {"symbol": "✅", "short": "Natural and authentic", "suggestion": "Excellent! This writing has personality and unpredictability that is difficult for AI to replicate."}
}


# ==========================================================
# SECTION 2: HEURISTIC ANALYSIS FUNCTIONS
# ==========================================================

def calculate_burstiness(text):
    """Measures the standard deviation of sentence lengths."""
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
    if len(sentences) < 2: return 0.0
    lengths = [len(s.split()) for s in sentences]
    return float(np.std(lengths) / np.mean(lengths))

def calculate_lexical_diversity(text):
    """Calculates the ratio of unique words to total words."""
    words = re.findall(r'\b\w+\b', text.lower())
    if not words: return 0.0
    return len(set(words)) / len(words)

def calculate_readability(text):
    """Calculates the Flesch-Kincaid grade level."""
    if len(re.findall(r'\b\w+\b', text)) < 10: return 50.0
    try:
        return textstat.flesch_kincaid_grade(text)
    except:
        return 50.0 # Default value on error

# ==========================================================
# SECTION 3: CORE ANALYSIS AND SCORING
# ==========================================================

def compute_human_score(perp, burst, diversity, readability_std):
    """Aggregates multiple metrics into a single human-likeness score."""
    # Perplexity Score (40%)
    if perp < AI_PERP_LOW: perp_score = (perp / AI_PERP_LOW) * 30
    elif perp < HUMAN_PERP_MIN: perp_score = 30 + ((perp - AI_PERP_LOW) / (HUMAN_PERP_MIN - AI_PERP_LOW)) * 30
    else: perp_score = min(60 + (perp - HUMAN_PERP_MIN) * 0.4, 100)

    # Burstiness Score (30%)
    burst_score = min(burst * 120, 100)

    # Diversity Score (20%)
    if diversity < LEXICAL_DIVERSITY_MIN: diversity_score = (diversity / LEXICAL_DIVERSITY_MIN) * 50
    else: diversity_score = min(50 + ((diversity - LEXICAL_DIVERSITY_MIN) / (LEXICAL_DIVERSITY_GOOD - LEXICAL_DIVERSITY_MIN)) * 50, 100)
    
    # Readability Uniformity Score (10%)
    readability_score = max(0, 100 - (readability_std / READABILITY_UNIFORMITY_THRESHOLD) * 100)

    # Weighted average
    human_score = (0.40 * perp_score + 0.30 * burst_score + 0.20 * diversity_score + 0.10 * readability_score)
    return round(max(min(human_score, 100), 0), 1)

def get_full_analysis(text, models):
    """
    Performs a comprehensive analysis of the text, combining model-based and heuristic methods.
    """
    # --- 1. OVERALL METRICS ---
    perp_overall = calculate_perplexity(text, models)
    roberta_score = calculate_roberta_score(text, models)
    burst_overall = calculate_burstiness(text)
    diversity_overall = calculate_lexical_diversity(text)

    # --- 2. SENTENCE-LEVEL ANALYSIS ---
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if not sentences:
        return {"composite_human_score": 0, "sentence_analysis": [], "error": "No sentences found."}

    sentence_analysis = []
    readability_scores = []
    mean_len = np.mean([len(s.split()) for s in sentences])

    for sentence in sentences:
        if len(sentence.split()) < 3: continue
        
        perp = calculate_perplexity(sentence, models)
        readability = calculate_readability(sentence)
        readability_scores.append(readability)
        
        # --- Flagging Logic ---
        flag = "HUMAN"
        if perp < AI_PERP_VERY_LOW: flag = "AI_VERY_PREDICTABLE"
        elif perp < AI_PERP_LOW: flag = "AI_PREDICTABLE"
        elif perp < HUMAN_PERP_MIN: flag = "MIXED"
        
        # Check for boilerplate phrases
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in AI_BOILERPLATE):
            flag = "BOILERPLATE"
            
        sentence_analysis.append({
            "sentence": sentence,
            "perplexity": perp,
            "length": len(sentence.split()),
            "readability": readability,
            "flag": flag,
            "suggestion_data": SUGGESTIONS.get(flag, SUGGESTIONS["HUMAN"])
        })
    
    readability_std = np.std(readability_scores) if len(readability_scores) > 1 else 0.0

    # --- 3. FINAL COMPOSITE SCORE ---
    composite_score = compute_human_score(perp_overall, burst_overall, diversity_overall, readability_std)

    return {
        "perp_overall": perp_overall,
        "roberta_detection_score": roberta_score,
        "burst_overall": burst_overall,
        "diversity_overall": diversity_overall,
        "readability_std": readability_std,
        "composite_human_score": composite_score,
        "sentence_analysis": sentence_analysis
    }