import json
import logging
import os
import re
from dotenv import load_dotenv
from fast_langdetect import detect
from openai import OpenAI
import spacy

# -------------------------------------------------------------------
# 0. Load Environment Variables for Background Worker
# -------------------------------------------------------------------
load_dotenv()  # Ensures GROQ_API_KEY is available inside ARQ workers

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# 1. Global Model Cache & Language Mapping
# -------------------------------------------------------------------
SPACY_MODEL_CACHE = {}

SUPPORTED_SPACY_LANGS = {
    "en": "en_core_web_sm",
    "es": "es_core_news_sm",
    "fr": "fr_core_news_sm",
    "de": "de_core_news_sm",
}


# -------------------------------------------------------------------
# 2. Universal Dynamic Language Router
# -------------------------------------------------------------------
def inspect_language_and_script(text: str) -> tuple[str, float]:
    """Extracts language code and confidence score safely from fast_langdetect."""
    try:
        raw_res = detect(text[:1000])

        if isinstance(raw_res, list) and len(raw_res) > 0:
            first_item = raw_res[0]
            if isinstance(first_item, dict):
                return first_item.get("lang", "en"), float(first_item.get("score", 1.0))
            elif isinstance(first_item, (tuple, list)):
                return str(first_item[0]), float(first_item[1]) if len(first_item) > 1 else 1.0
            else:
                return str(first_item), 1.0
        elif isinstance(raw_res, dict):
            return raw_res.get("lang", "en"), float(raw_res.get("score", 1.0))
        elif isinstance(raw_res, tuple):
            return str(raw_res[0]), float(raw_res[1]) if len(raw_res) > 1 else 1.0
        elif isinstance(raw_res, str):
            return raw_res, 1.0
        else:
            return "en", 1.0
    except Exception as e:
        logger.warning(f"Language detection failed ({e}), defaulting to 'en'")
        return "en", 0.0


def requires_llm_processing(text: str, detected_lang: str, confidence: float) -> bool:
    """Universal Heuristic: Checks for non-ASCII characters, low-confidence transliteration,

    or non-supported spaCy languages dynamically without script-specific hardcoding.
    """
    # 1. Universal Script Check: Matches any non-ASCII character (U+0080 and above)
    # Covers ALL global non-Latin scripts (Devanagari, Kanji, Hanzi, Arabic, Cyrillic, Thai, Greek, etc.)
    non_ascii_characters = re.findall(r"[^\x00-\x7F]", text)
    if len(non_ascii_characters) > 5:
        logger.info(
            f"[Router Heuristic] Non-ASCII native script detected ({len(non_ascii_characters)} chars). Routing to Groq LLM..."
        )
        return True

    # 2. Low-confidence detection for Romanized / Transliterated text (e.g., Romanized Hindi/Nepali/Japanese)
    if detected_lang == "en" and confidence < 0.75:
        logger.info(
            f"[Router Heuristic] Low English confidence ({confidence:.2f}). Routing to Groq LLM..."
        )
        return True

    # 3. Any language not in spaCy's standard localized models
    if detected_lang not in SUPPORTED_SPACY_LANGS:
        logger.info(
            f"[Router Heuristic] Language '{detected_lang}' not in local spaCy suite. Routing to Groq LLM..."
        )
        return True

    return False


# -------------------------------------------------------------------
# 3. Helper: Lazy Loading Model Fetcher
# -------------------------------------------------------------------
def get_spacy_model(lang_code: str):
    """Lazy loads spaCy models on-demand and caches them in RAM."""
    model_name = SUPPORTED_SPACY_LANGS.get(lang_code)
    if not model_name:
        return None

    if lang_code not in SPACY_MODEL_CACHE:
        logger.info(f"[NLP Cache Miss] Loading spaCy model '{model_name}' into RAM...")
        try:
            SPACY_MODEL_CACHE[lang_code] = spacy.load(model_name)
        except Exception as e:
            logger.error(f"Failed to load spaCy model {model_name}: {e}")
            return None
    else:
        logger.info(f"[NLP Cache Hit] Reusing cached spaCy model for '{lang_code}'")

    return SPACY_MODEL_CACHE[lang_code]


# -------------------------------------------------------------------
# 4. Engine A: Local spaCy Extraction (Standard Latin / Pure English)
# -------------------------------------------------------------------
def extract_spacy_entities(text: str, nlp_model) -> dict[str, list[str]]:
    """Runs fast local extraction using loaded spaCy model."""
    doc = nlp_model(text)
    entities = {}

    for ent in doc.ents:
        clean_text = ent.text.strip()
        if clean_text:
            label = ent.label_
            if label not in entities:
                entities[label] = set()
            entities[label].add(clean_text)

    return {label: sorted(list(values)) for label, values in entities.items()}


# -------------------------------------------------------------------
# 5. Engine B: Universal LLM Extraction (Handles ALL Global Languages & Romanization)
# -------------------------------------------------------------------
def extract_llm_entities(text: str) -> dict[str, list[str]]:
    """Universal LLM engine for non-Latin scripts, mixed documents, and romanized text."""
    api_key = os.getenv("GROQ_API_KEY", "")

    if not api_key:
        logger.error(
            "[NLP Error] GROQ_API_KEY is not set in environment or .env file! Skipping LLM extraction."
        )
        return {}

    llm_client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )

    # Select an available chat model dynamically from Groq
    target_model = "llama-3.3-70b-versatile"
    try:
        available_models = [m.id for m in llm_client.models.list().data]
        candidates = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ]

        for cand in candidates:
            if cand in available_models:
                target_model = cand
                break
    except Exception as e:
        logger.warning(f"Failed to query Groq models ({e}). Defaulting to: {target_model}")

    prompt = f"""
You are a universal multilingual Named Entity Recognition (NER) system.
Extract structured entities from the input text regardless of language, script, or transliteration style.

Input text could be:
- Any native non-Latin script (Devanagari, Kanji, Hanzi, Arabic, Cyrillic, Thai, Greek, etc.)
- Romanized/Transliterated text (e.g., non-English text written using Latin alphabets)
- Mixed-language documents (e.g., English headers with regional language content)

Categories to extract:
- PERSON: Names of individuals or people
- ORG: Company names, stores, organizations, institutions, government bodies
- GPE: Cities, districts, states, countries, towns, locations, addresses
- DATE: Dates in any format or calendar system
- MONEY: Financial amounts, currency totals, prices
- PHONE: Contact phone/mobile numbers
- PRODUCT: Specific items, goods, produce, or services listed

Rules:
1. Do NOT categorize currency markers or symbols as PERSON or GPE.
2. Return ONLY a valid, raw JSON object matching the exact key structure below. Do not wrap in markdown or add explanations.

JSON Structure:
{{
  "PERSON": [...],
  "GPE": [...],
  "ORG": [...],
  "MONEY": [...],
  "DATE": [...],
  "PHONE": [...],
  "PRODUCT": [...]
}}

DOCUMENT TEXT:
{text[:4000]}
"""

    messages = [{"role": "user", "content": prompt}]

    try:
        response = llm_client.chat.completions.create(
            model=target_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        return data.get("entities", data)
    except Exception as e:
        logger.warning(f"[JSON Mode Failed ({e})]: Retrying standard completion fallback...")
        try:
            response = llm_client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=0.0,
            )
            content = response.choices[0].message.content.strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            return data.get("entities", data)
        except Exception as inner_e:
            logger.error(f"[LLM Fallback Extraction Error]: {inner_e}")
            return {}


# -------------------------------------------------------------------
# 6. Main Entry Point: Router Function
# -------------------------------------------------------------------
def extract_entities_from_text(text: str) -> dict[str, list[str]]:
    if not text or not text.strip():
        return {}

    detected_lang, confidence = inspect_language_and_script(text)
    logger.info(f"[Language Router] Detected: '{detected_lang}' (Confidence: {confidence:.2f})")

    # Step 1: Check universal dynamic heuristics
    if requires_llm_processing(text, detected_lang, confidence):
        return extract_llm_entities(text)

    # Step 2: Route standard, high-confidence text to local spaCy engine
    nlp_model = get_spacy_model(detected_lang)
    if nlp_model:
        logger.info(f"[Language Router] Processing via spaCy '{SUPPORTED_SPACY_LANGS[detected_lang]}'...")
        return extract_spacy_entities(text, nlp_model)

    # Step 3: Default fallback
    logger.info("[Language Router] Fallback routing to Groq LLM...")
    return extract_llm_entities(text)