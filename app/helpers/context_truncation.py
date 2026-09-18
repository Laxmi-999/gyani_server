# app/helpers/context_truncation.py

MAX_CHARS_PER_NOTE = 1500  # roughly ~375 tokens per note, adjust as needed


def truncate_content(text: str, max_chars: int = MAX_CHARS_PER_NOTE) -> str:
    """Truncates a note's content to a safe character limit before it's included
    in an LLM prompt, to avoid exceeding the model's context window when multiple
    notes are combined into one request."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "... [truncated]"