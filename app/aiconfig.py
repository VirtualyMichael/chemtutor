"""Which local AI server and model ChemTutor uses: Ollama or LM Studio (any OpenAI-compatible server works).

Order of precedence: LLM_URL / LLM_MODEL (or --llm-url / --model) > the choice saved in <library>/ai.json
(made from the model badge in the app) > automatic: the default model if a server has it, else the best-looking
chat model on the first server found. Stdlib only.
"""
from __future__ import annotations
import json, re, urllib.request

from . import library

DEFAULT_MODEL = "qwen2.5:7b"
BACKENDS = [("Ollama", "http://localhost:11434/v1"), ("LM Studio", "http://localhost:1234/v1")]
ALIASES = {"ollama": BACKENDS[0][1], "lmstudio": BACKENDS[1][1], "lm-studio": BACKENDS[1][1], "lm studio": BACKENDS[1][1]}
NOT_CHAT = ("embed", "rerank", "whisper", "tts", "clip", "voxtral", "audio", "vision-only")
AVOID = ("uncensored", "abliterated", "heretic", "coder", "roleplay", "nsfw")  # fine-tunes that make worse tutors
SWEET_SPOT_B = 14  # largest size picked automatically: bigger models are often too slow on a home PC (you can still choose them)


def resolve_url(value: str) -> str:
    """Accepts a full URL or the words 'ollama' / 'lmstudio'."""
    return ALIASES.get((value or "").strip().lower(), value)


def backend_name(url: str) -> str:
    u = (url or "").rstrip("/")
    for name, b in BACKENDS:
        if u == b.rstrip("/"):
            return name
    return "AI server"


def _file():
    return library.HOME / "ai.json"


def load() -> dict:
    try:
        d = json.loads(_file().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save(url: str, model: str) -> None:
    _file().parent.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps({"url": url, "model": model}), encoding="utf-8")


def forget() -> None:
    try:
        _file().unlink()
    except OSError:
        pass


def list_models(url: str, timeout: float = 1.0) -> list[str] | None:
    """Chat model ids offered by the server, or None if it is not reachable."""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/models", timeout=timeout) as r:
            ids = [m.get("id", "") for m in json.load(r).get("data", [])]
    except Exception:  # noqa: BLE001  (refused, timeout, not JSON...)
        return None
    return [i for i in ids if i and not any(w in i.lower() for w in NOT_CHAT)]


def detect(extra_url: str | None = None) -> list[dict]:
    """[{name, url, up, models}] for every known server (plus the configured one if it is somewhere else)."""
    urls = [u for _, u in BACKENDS]
    if extra_url and extra_url.rstrip("/") not in [u.rstrip("/") for u in urls]:
        urls.append(extra_url)
    out = []
    for u in urls:
        m = list_models(u, 0.6)
        out.append({"name": backend_name(u), "url": u, "up": m is not None, "models": m or []})
    return out


def has_model(model: str, names: list[str]) -> bool:
    """Exact match; for Ollama a name without a tag ('qwen2.5') matches any tag."""
    base = model.split(":")[0]
    return any(n == model or (":" not in model and n.split(":")[0] == base) for n in names)


def _size(name: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", name.lower().replace("-", " ").replace("_", " "))
    return float(m.group(1)) if m else 0.0


def best_model(names: list[str]) -> str | None:
    """A sensible default tutor: a plain chat model, the largest up to ~14B (bigger ones are slow on most PCs);
    if everything is bigger, the smallest. Models that do not say their size come last. You can always choose another."""
    if not names:
        return None
    plain = [n for n in names if not any(w in n.lower() for w in AVOID)] or names
    sized = [n for n in plain if _size(n)]
    fit = [n for n in sized if _size(n) <= SWEET_SPOT_B]
    if fit:
        return max(fit, key=lambda n: (_size(n), -plain.index(n)))
    if sized:
        return min(sized, key=_size)
    return plain[0]


def auto_pick(found: list[dict], wanted: str = DEFAULT_MODEL, prefer_url: str | None = None) -> tuple[str, str] | None:
    """(url, model) from detect() output, or None if no server has any chat model."""
    ups = [b for b in found if b["up"] and b["models"]]
    if prefer_url:
        ups.sort(key=lambda b: b["url"].rstrip("/") != prefer_url.rstrip("/"))
    for b in ups:
        if has_model(wanted, b["models"]):
            exact = wanted if wanted in b["models"] else next(n for n in b["models"] if n.split(":")[0] == wanted.split(":")[0])
            return b["url"], exact
    return (ups[0]["url"], best_model(ups[0]["models"])) if ups else None
