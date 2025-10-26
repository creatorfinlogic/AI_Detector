

# /ai_detector_pro/models.py

import streamlit as st
import torch
import torch.nn.functional as F
from transformers import (
    GPT2LMHeadModel, GPT2Tokenizer,
    AutoModelForSequenceClassification, AutoTokenizer
)

@st.cache_resource(show_spinner="Loading AI models...")
def load_models():
    """
    Loads and caches the GPT-2 and RoBERTa models and tokenizers.
    This function runs only once per session.
    """
    try:
        # Using smaller models for better performance on free-tier hosting
        # GPT-2 small for perplexity calculation
        gpt2_tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        gpt2_model = GPT2LMHeadModel.from_pretrained("gpt2")
        gpt2_model.eval() # Set to evaluation mode

        # RoBERTa detector model
        roberta_tokenizer = AutoTokenizer.from_pretrained("roberta-large-openai-detector")
        roberta_model = AutoModelForSequenceClassification.from_pretrained("roberta-large-openai-detector")
        roberta_model.eval() # Set to evaluation mode

        return {
            "gpt2_tok": gpt2_tokenizer, "gpt2_model": gpt2_model,
            "roberta_tok": roberta_tokenizer, "roberta_model": roberta_model
        }
    except Exception as e:
        st.error(f"Error loading models: {e}. The app may not function correctly.")
        return None

def calculate_perplexity(text, models):
    """Calculates the perplexity of a given text using the cached GPT-2 model."""
    if not models: return 1000.0
    tokenizer = models["gpt2_tok"]
    model = models["gpt2_model"]
    
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=1024)
    if inputs["input_ids"].size(1) < 2: return 1000.0 # Perplexity is undefined for very short text

    with torch.no_grad():
        loss = model(**inputs, labels=inputs["input_ids"]).loss
    
    return float(torch.exp(loss))

def calculate_roberta_score(text, models):
    """Calculates the 'human-likeness' probability using the cached RoBERTa model."""
    if not models: return 50.0 # Default to neutral if model fails
    tokenizer = models["roberta_tok"]
    model = models["roberta_model"]
    
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    
    with torch.no_grad():
        logits = model(**inputs).logits
    
    # The model outputs probabilities for ["AI", "Human"]. We want the "Human" probability.
    probabilities = F.softmax(logits, dim=1).squeeze().tolist()
    human_probability = probabilities[1] * 100
    
    return float(human_probability)