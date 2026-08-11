import re
import unicodedata


STOPWORDS = {
    "a", "al", "como", "con", "cual", "cuando", "de", "del",
    "el", "en", "es", "esta", "la", "las", "lo", "los", "para",
    "por", "que", "se", "su", "un", "una", "y", "and", "is",
    "of", "the", "to",
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", normalize_text(text))
        if token not in STOPWORDS
    ]
