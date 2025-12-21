# /ai_detector_pro/models.py
# VERSION: 2.0 – Stable (Detection Models Only)

import streamlit as st
import torch
import torch.nn.functional as F
from transformers import (
    GPT2LMHeadModel,
    GPT2Tokenizer,
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

# ==========================================================
# MODEL LOADER
# ==========================================================
@st.cache_resource(show_spinner="Loading AI models...")
def load_models():
    """
    Loads and caches:
    - GPT-2 (for perplexity / predictability)
    - RoBERTa OpenAI Detector (AI vs Human classification)

    Runs once per Streamlit session.
    """
    try:
        # GPT-2 (small) for perplexity
        gpt2_tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        gpt2_model = GPT2LMHeadModel.from_pretrained("gpt2")
        gpt2_model.eval()

        # RoBERTa OpenAI detector
        roberta_tokenizer = AutoTokenizer.from_pretrained(
            "roberta-large-openai-detector"
        )
        roberta_model = AutoModelForSequenceClassification.from_pretrained(
            "roberta-large-openai-detector"
        )
        roberta_model.eval()

        return {
            "gpt2_tok": gpt2_tokenizer,
            "gpt2_model": gpt2_model,
            "roberta_tok": roberta_tokenizer,
            "roberta_model": roberta_model,
        }

    except Exception as e:
        st.error(
            f"❌ Error loading AI models: {e}\n"
            "The app may not function correctly."
        )
        return None

# ==========================================================
# PERPLEXITY (GPT-2)
# ==========================================================
def calculate_perplexity(text, models):
    """
    Calculates GPT-2 perplexity.
    Lower = more predictable (AI-like)
    Higher = more varied (human-like)
    """
    if not models:
        return 1000.0

    tokenizer = models["gpt2_tok"]
    model = models["gpt2_model"]

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=1024,
    )

    if inputs["input_ids"].size(1) < 2:
        return 1000.0

    with torch.no_grad():
        loss = model(
            **inputs,
            labels=inputs["input_ids"]
        ).loss

    return float(torch.exp(loss))

# ==========================================================
# AI vs HUMAN PROBABILITY (RoBERTa)
# ==========================================================
def calculate_roberta_score(text, models):
    """
    Returns HUMAN probability (0–100).
    AI probability = 100 - this value.
    """
    if not models:
        return 50.0

    tokenizer = models["roberta_tok"]
    model = models["roberta_model"]

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )

    with torch.no_grad():
        logits = model(**inputs).logits

    probs = F.softmax(logits, dim=1).squeeze().tolist()

    # Index 1 = Human (per model documentation)
    return float(probs[1] * 100)

# ==========================================================
# (OPTIONAL) LEGACY GPT-4o REWRITE – DEPRECATED
# ==========================================================
def get_gpt4o_rewrite(sentence, api_key):
    """
    DEPRECATED.
    Kept for backward compatibility only.
    Use rewrite_text_for_human_score() in analysis.py instead.
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional editor. "
                        "Rewrite the sentence clearly and actively. "
                        "Preserve all facts."
                    ),
                },
                {"role": "user", "content": sentence},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"API Error: {str(e)}"
