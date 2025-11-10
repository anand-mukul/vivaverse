# utils/text_utils.py
"""
Utility functions for text preprocessing, keyword extraction, and improvement tips.
Used by feedback_engine.py in EchoViva 2.0
"""

import re
import string
import spacy

# Load spaCy lightweight English model (if not already loaded)
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    # fallback if model not installed
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


def clean_text(text: str) -> str:
    """Normalize text by lowercasing, removing punctuation and extra spaces."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text


def extract_keywords(text: str) -> set:
    """
    Extract meaningful keywords (nouns, verbs, adjectives) using spaCy.
    Returns a set of lemmatized words.
    """
    if not text:
        return set()
    doc = nlp(text)
    keywords = set()
    for token in doc:
        if token.is_stop or token.is_punct:
            continue
        if token.pos_ in ("NOUN", "VERB", "ADJ"):
            keywords.add(token.lemma_)
    return keywords


def keyword_similarity(text1: str, text2: str) -> float:
    """
    Compute Jaccard similarity between sets of keywords.
    Returns 0–1 range (1 = perfect keyword match).
    """
    kw1 = extract_keywords(text1)
    kw2 = extract_keywords(text2)
    if not kw1 or not kw2:
        return 0.0
    intersection = len(kw1.intersection(kw2))
    union = len(kw1.union(kw2))
    return round(intersection / union, 4)


def get_improvement_tips(user_answer: str, correct_answer: str) -> str:
    """
    Provide simple improvement tips based on missing keywords.
    """
    kw_user = extract_keywords(user_answer)
    kw_correct = extract_keywords(correct_answer)
    missing = kw_correct - kw_user
    if not missing:
        return ""
    sample = ", ".join(list(missing)[:4])
    return f"Consider including concepts like: {sample}."
