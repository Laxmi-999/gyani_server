import json
import logging
import os
from fast_langdetect import detect
from openai import OpenAI
import spacy

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
# 2. Helper: Lazy Loading Model Fetcher (Caching & Memory)
# -------------------------------------------------------------------
def get_spacy_model(lang_code: str):
    """Lazy loads spaCy models on-demand and caches them in RAM."""
    model_name = SUPPORTED_SPACY_LANGS.get(lang_code)
    if not model_name:
        return None

    if lang_code not in SPACY_MODEL_CACHE:
        logger.info(
            f"[NLP Cache Miss] Loading spaCy model '{model_name}' into RAM..."
        )
        try:
            SPACY_MODEL_CACHE[lang_code] = spacy.load(model_name)
        except Exception as e:
            logger.error(f"Failed to load spaCy model {model_name}: {e}")
            return None
    else:
        logger.info(
            f"[NLP Cache Hit] Reusing cached spaCy model for '{lang_code}'"
        )

    return SPACY_MODEL_CACHE[lang_code]


# -------------------------------------------------------------------
# 3. Engine A: Local spaCy Extraction
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
# 4. Engine B: LLM Zero-Shot Fallback (Nepali & Unsupported Languages)
# -------------------------------------------------------------------
def extract_llm_entities(text: str) -> dict[str, list[str]]:
    """Fallback LLM engine for unsupported languages (e.g. Nepali, Arabic)."""

    api_key = os.getenv("GROQ_API_KEY", "")

    if not api_key:
        logger.warning(
            "GROQ_API_KEY not configured in environment. Skipping fallback extraction."
        )
        return {}

    llm_client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )

    # 1. Dynamically find a valid, active chat model from Groq
    target_model = "llama-3.3-70b-versatile"
    try:
        available_models = [m.id for m in llm_client.models.list().data]
        
        # Priority list for general chat models supporting structured tasks
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
        logger.warning(f"Failed to query Groq models ({e}). Using default: {target_model}")

    prompt = f"""
    You are an expert multi-lingual Named Entity Recognition (NER) system.
    Extract key entities from the provided text regardless of language (e.g. Nepali, Arabic, Hindi, etc.).
    Identify entities such as PERSON, ORG, GPE, DATE, MONEY, AMOUNT, BANK, TAX_ID.
    
    Return strictly valid JSON in this structure:
    {{
      "PERSON": ["..."],
      "GPE": ["..."],
      "ORG": ["..."],
      "MONEY": ["..."]
    }}

    TEXT:
    {text[:3000]}
    """

    # Single-message payload to guarantee compatibility across text-classification & chat models
    messages = [{"role": "user", "content": prompt}]

    # 2. Try request with response_format, fallback to standard parsing if backend templating fails
    try:
        response = llm_client.chat.completions.create(
            model=target_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return data.get("entities", data)
    except Exception as e:
        logger.warning(f"[JSON Mode Failed ({e})]: Attempting standard completion fallback...")
        try:
            # Fallback call without response_format constraint
            response = llm_client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=0.1,
            )
            content = response.choices[0].message.content
            
            # Clean markdown codeblocks if model wraps JSON in ```json ... ```
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
# 5. Main Entry Point: Router Function
# -------------------------------------------------------------------
def extract_entities_from_text(text: str) -> dict[str, list[str]]:
    if not text or not text.strip():
        return {}

    # Step 1: Safe Language Detection
    try:
        raw_res = detect(text[:1000])

        if isinstance(raw_res, list) and len(raw_res) > 0:
            first_item = raw_res[0]
            if isinstance(first_item, dict):
                detected_lang = first_item.get("lang", "en")
            elif isinstance(first_item, (tuple, list)):
                detected_lang = first_item[0]
            else:
                detected_lang = str(first_item)
        elif isinstance(raw_res, dict):
            detected_lang = raw_res.get("lang", "en")
        elif isinstance(raw_res, tuple):
            detected_lang = raw_res[0]
        elif isinstance(raw_res, str):
            detected_lang = raw_res
        else:
            detected_lang = "en"

        logger.info(f"[Language Router] Detected language: '{detected_lang}'")

    except Exception as e:
        logger.warning(
            f"Language detection failed ({e}), defaulting to English"
        )
        detected_lang = "en"

    # Step 2: Route to local spaCy if supported ('en', 'es', 'fr', 'de')
    if detected_lang in SUPPORTED_SPACY_LANGS:
        nlp_model = get_spacy_model(detected_lang)
        if nlp_model:
            return extract_spacy_entities(text, nlp_model)

    # Step 3: Route to Groq LLM Fallback for non-spaCy languages (e.g. 'ne' for Nepali)
    logger.info(
        f"Language '{detected_lang}' not in spaCy suite. Routing to Groq LLM..."
    )
    return extract_llm_entities(text)