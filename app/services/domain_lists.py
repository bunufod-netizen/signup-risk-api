from functools import lru_cache
from pathlib import Path

FREE_PROVIDERS = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "proton.me", "protonmail.com"}
ROLE_LOCAL_PARTS = {"admin", "support", "sales", "billing", "info", "contact", "help", "webmaster", "noreply", "no-reply"}
TYPO_SUGGESTIONS = {"gmial.com": "gmail.com", "gamil.com": "gmail.com", "gmail.con": "gmail.com", "hotmial.com": "hotmail.com", "outlok.com": "outlook.com", "yaho.com": "yahoo.com"}


@lru_cache
def disposable_domains() -> frozenset[str]:
    path = Path(__file__).resolve().parents[2] / "data" / "disposable_domains.txt"
    try:
        return frozenset(line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#"))
    except OSError:
        return frozenset()


def is_disposable(domain: str) -> bool:
    domains = disposable_domains()
    return domain in domains or any(domain.endswith(f".{item}") for item in domains)
