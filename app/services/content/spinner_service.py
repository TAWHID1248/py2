"""Two-pass spintax + WordNet synonym engine."""
import re
import random
from app.core.logger import get_logger

log = get_logger(__name__)

_SPINTAX_RE = re.compile(r"\{([^{}]+)\}")


def resolve_spintax(text: str, seed: int | None = None) -> str:
    rng = random.Random(seed)

    def _replace(match: re.Match) -> str:
        return rng.choice(match.group(1).split("|"))

    prev = None
    while prev != text:
        prev = text
        text = _SPINTAX_RE.sub(_replace, text)
    return text


def _ensure_wordnet():
    import nltk
    try:
        from nltk.corpus import wordnet
        wordnet.synsets("test")
        return wordnet
    except LookupError:
        log.info("Downloading NLTK WordNet corpus…")
        nltk.download("wordnet", quiet=True)
        nltk.download("omw-1.4", quiet=True)
        from nltk.corpus import wordnet
        return wordnet


def apply_synonyms(text: str, seed: int | None = None, intensity: float = 0.3) -> str:
    """Replace ~intensity fraction of words with WordNet synonyms."""
    try:
        wordnet = _ensure_wordnet()
    except Exception:
        log.warning("nltk WordNet unavailable — skipping synonym pass")
        return text

    rng = random.Random(seed)
    words = text.split()
    result = []
    for word in words:
        if rng.random() > intensity:
            result.append(word)
            continue
        # strip punctuation for lookup, reattach afterward
        stripped = word.strip(".,!?;:\"'()")
        punct = word[len(stripped):]
        synsets = wordnet.synsets(stripped.lower())
        if synsets:
            lemmas = list({
                l.name().replace("_", " ")
                for s in synsets[:2]
                for l in s.lemmas()
                if l.name().lower() != stripped.lower()
            })
            if lemmas:
                result.append(rng.choice(lemmas) + punct)
                continue
        result.append(word)
    return " ".join(result)


def spin(text: str, use_synonyms: bool = False, seed: int | None = None) -> str:
    text = resolve_spintax(text, seed)
    if use_synonyms:
        text = apply_synonyms(text, seed)
    return text


def download_nltk_data():
    """Pre-download NLTK data. Call once at startup in a background thread."""
    import threading
    def _dl():
        try:
            _ensure_wordnet()
            log.info("NLTK WordNet ready")
        except Exception as e:
            log.warning("NLTK download failed: %s", e)
    threading.Thread(target=_dl, daemon=True).start()
