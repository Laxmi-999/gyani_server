# app/helpers/query_expansion.py
import logging
import re

logger = logging.getLogger(__name__)

LANGUAGE_DIRECTIVE_PATTERN = re.compile(
    r"\b(in|answer in|respond in|reply in|please answer in)\s+[a-zA-Z\u0900-\u097F]+\??\s*$",
    re.IGNORECASE,
)

def strip_language_directive(question: str) -> str:
    """Removes a trailing language instruction (e.g. 'in nepali', 'answer in hindi')
    from a question, so it doesn't pollute keyword/semantic search. The full original
    question (with the directive intact) should still be used for the final LLM prompt."""
    stripped = LANGUAGE_DIRECTIVE_PATTERN.sub("", question).strip()
    return stripped if stripped else question


def expand_query_variants(llm_client, target_model: str, question: str) -> list[str]:
    """Asks the LLM for translated/transliterated variants of the question, to widen
    retrieval across languages and scripts."""
    prompt = (
        "The following question may be written in romanized/transliterated form of another language, "
        "or in a language other than English. Produce exactly 2 lines:\n"
        "Line 1: The question translated into clear, natural English.\n"
        "Line 2: The question written in its native script if it appears to be a romanized version of "
        "a non-English language (e.g. Devanagari for Nepali/Hindi). If the question is already in English "
        "and has no other-language equivalent, repeat the original question on this line instead.\n\n"
        "Return ONLY the 2 lines, no labels, no numbering, no extra commentary.\n\n"
        f"Question: {question}"
    )
    try:
        response = llm_client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
            reasoning_effort="low",

        )
        raw = (response.choices[0].message.content or "").strip()
        logger.info(f"[RAG Chat] Full message object: {response.choices[0].message!r}")
        logger.info(f"[RAG Chat] Raw expansion output: {raw!r}")
        if not raw:
            logger.warning("[RAG Chat] Expansion returned empty content, retrying with a simpler prompt")
            fallback_response = llm_client.chat.completions.create(
                model=target_model,
                messages=[{
                    "role": "user",
                    "content": f"Translate this into English, and also into Devanagari script if it is Nepali or Hindi: {question}"
                }],
                temperature=0.2,
                max_tokens=300,
                reasoning_effort="low",

            )
            raw = (fallback_response.choices[0].message.content or "").strip()
            logger.info(f"[RAG Chat] Fallback expansion output: {raw!r}")

        variants = [line.strip() for line in raw.splitlines() if line.strip()]
        return variants[:2]
    except Exception as e:
        logger.warning(f"[RAG Chat] Query expansion failed, continuing with original query only: {e}")
        return []


def merge_search_results(result_sets: list) -> list:
    """Merges multiple perform_hybrid_search result sets, de-duplicating by note id
    and keeping the highest rrf_score seen for each note across all query variants."""
    merged: dict[int, object] = {}
    for rows in result_sets:
        for row in rows:
            if row.id not in merged or row.rrf_score > merged[row.id].rrf_score:
                merged[row.id] = row
    return sorted(merged.values(), key=lambda r: r.rrf_score, reverse=True)