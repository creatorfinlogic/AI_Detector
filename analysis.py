# ==========================================================
# analysis.py
# VERSION: 2.0 – Phase 2.1 + 2.2
# Detection + Human Rewrite + Grammar + Paraphrase + Proofreading
# ==========================================================

import re
import numpy as np
import textstat
from openai import OpenAI

from models import calculate_perplexity, calculate_roberta_score

# ==========================================================
# CONSTANTS
# ==========================================================
AI_PERP_VERY_LOW = 15.0
AI_PERP_LOW = 30.0
HUMAN_PERP_MIN = 50.0

LEXICAL_DIVERSITY_GOOD = 0.60
READABILITY_UNIFORMITY_THRESHOLD = 4.0

AI_BOILERPLATE = [
    r"In conclusion",
    r"Furthermore",
    r"Moreover",
    r"Thus",
    r"Hence",
    r"It is imperative",
]

# ==========================================================
# SUGGESTIONS (UI CONTRACT)
# ==========================================================
SUGGESTIONS = {
    "AI_VERY_PREDICTABLE": {
        "symbol": "🔴",
        "short": "Highly predictable",
        "suggestion": "Add specificity, opinion, or lived experience.",
    },
    "AI_PREDICTABLE": {
        "symbol": "🟠",
        "short": "Predictable phrasing",
        "suggestion": "Vary sentence structure or introduce concrete examples.",
    },
    "BOILERPLATE": {
        "symbol": "🟤",
        "short": "Generic transition",
        "suggestion": "Replace this with a more conversational transition.",
    },
    "HUMAN": {
        "symbol": "✅",
        "short": "Natural",
        "suggestion": "This sentence sounds natural and human.",
    },
}

# ==========================================================
# METRICS
# ==========================================================
def calculate_burstiness(text: str) -> float:
    sentences = [s for s in re.split(r"[.!?]", text) if s.strip()]
    if len(sentences) < 2:
        return 0.0
    lengths = [len(s.split()) for s in sentences]
    return float(np.std(lengths) / np.mean(lengths))


def calculate_lexical_diversity(text: str) -> float:
    words = re.findall(r"\b\w+\b", text.lower())
    return len(set(words)) / len(words) if words else 0.0


def calculate_readability(text: str) -> float:
    try:
        return textstat.flesch_kincaid_grade(text)
    except Exception:
        return 50.0

# ==========================================================
# SCORING
# ==========================================================
def compute_human_score(perp, burst, diversity, readability_std):
    perp_score = min((perp / HUMAN_PERP_MIN) * 60, 100)
    burst_score = min(burst * 120, 100)
    diversity_score = min((diversity / LEXICAL_DIVERSITY_GOOD) * 100, 100)
    read_score = max(
        0,
        100 - (readability_std / READABILITY_UNIFORMITY_THRESHOLD) * 100
    )

    return round(
        0.4 * perp_score +
        0.3 * burst_score +
        0.2 * diversity_score +
        0.1 * read_score,
        1
    )

# ==========================================================
# PROOFREADING (FULL – SEPARATE MODE)
# ==========================================================
def proofreading_suggestions(text: str, api_key: str) -> str:
    if not api_key:
        raise ValueError("OpenAI API key missing")

    client = OpenAI(api_key=api_key)

    prompt = f"""
    Proofread the following text.

    Rules:
    - Fix grammar and spelling
    - Improve clarity and sentence flow
    - Keep original meaning
    - Do NOT rewrite aggressively
    - Return only the improved text

    TEXT:
    {text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()

# ==========================================================
# GRAMMAR ONLY (SAFE)
# ==========================================================
def grammar_fix_only(text: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)

    prompt = f"""
    Fix grammar, spelling, and punctuation only.
    Do not rephrase or change tone.
    Return only corrected text.

    TEXT:
    {text}
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    return res.choices[0].message.content.strip()

# ==========================================================
# PARAPHRASE
# ==========================================================
def paraphrase_text(text: str, api_key: str, mode: str = "Simplify") -> str:
    client = OpenAI(api_key=api_key)

    instruction_map = {
        "Simplify": "Simplify the language.",
        "Shorten": "Make the text concise.",
        "Expand": "Expand with explanation.",
        "Formal": "Make the tone formal.",
        "Conversational": "Make it conversational.",
    }

    instruction = instruction_map.get(mode, "Simplify the language.")

    prompt = f"""
    {instruction}
    Preserve meaning and facts.
    Return only paraphrased text.

    TEXT:
    {text}
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    return res.choices[0].message.content.strip()

# ==========================================================
# HUMAN SCORE REWRITE (INTENSITY AWARE)
# ==========================================================
def rewrite_text_for_human_score(
    text: str,
    analysis: dict,
    api_key: str,
    intensity: str = "Balanced",
) -> str:

    client = OpenAI(api_key=api_key)

    style_map = {
        "Conservative": "Make minimal changes. Slight variation only.",
        "Balanced": "Balance clarity with human rhythm. Avoid over-polishing.",
        "Aggressive": "Increase unpredictability, rhythm variation, mild imperfection.",
    }

    style = style_map.get(intensity, style_map["Balanced"])

    prompt = f"""
    Rewrite the text to sound more human.

    Rules:
    - Preserve facts and meaning
    - {style}
    - Avoid generic phrasing
    - Vary sentence length
    - Do not add information
    - Return only rewritten text

    TEXT:
    {text}
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.45,
    )

    return res.choices[0].message.content.strip()

# ==========================================================
# FULL ANALYSIS (SCHEMA SAFE)
# ==========================================================
def get_full_analysis(text: str, models: dict) -> dict:

    perp_overall = calculate_perplexity(text, models)
    roberta_score = calculate_roberta_score(text, models)

    burst = calculate_burstiness(text)
    diversity = calculate_lexical_diversity(text)

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if s.strip()
    ]

    sentence_analysis = []
    readability_scores = []

    for s in sentences:
        if len(s.split()) < 3:
            continue

        perp = calculate_perplexity(s, models)
        read = calculate_readability(s)
        readability_scores.append(read)

        flag = "HUMAN"
        if perp < AI_PERP_VERY_LOW:
            flag = "AI_VERY_PREDICTABLE"
        elif perp < AI_PERP_LOW:
            flag = "AI_PREDICTABLE"

        if any(re.search(p, s, re.I) for p in AI_BOILERPLATE):
            flag = "BOILERPLATE"

        sentence_analysis.append(
            {
                "sentence": s,
                "perplexity": perp,
                "readability": read,
                "flag": flag,
                "suggestion_data": SUGGESTIONS.get(
                    flag,
                    {
                        "symbol": "ℹ️",
                        "short": "Review",
                        "suggestion": "Consider revising this sentence for clarity.",
                    },
                ),
            }
        )

    score = compute_human_score(
        perp_overall,
        burst,
        diversity,
        np.std(readability_scores) if len(readability_scores) > 1 else 0.0,
    )

    return {
        "perp_overall": perp_overall,
        "roberta_detection_score": roberta_score,
        "burst_overall": burst,
        "diversity_overall": diversity,
        "composite_human_score": score,
        "sentence_analysis": sentence_analysis,
    }
