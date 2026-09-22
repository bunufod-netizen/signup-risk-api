from dataclasses import dataclass


@dataclass(frozen=True)
class RiskResult:
    score: int
    risk: str
    reasons: list[str]


def calculate_risk(*, valid_format: bool, domain_exists: bool | None, mx_exists: bool | None, dns_uncertain: bool, disposable: bool, role_account: bool, typo_suggestion: str | None) -> RiskResult:
    score, reasons = 0, []
    if not valid_format:
        score += 100; reasons.append("Invalid email format")
    else:
        if domain_exists is False:
            score += 80; reasons.append("Domain does not exist")
        if mx_exists is False:
            score += 35; reasons.append("No MX records found")
        if dns_uncertain:
            reasons.append("DNS verification temporarily unavailable")
        if disposable:
            score += 80; reasons.append("Disposable email provider")
        if role_account:
            score += 10; reasons.append("Role-based email address")
        if typo_suggestion:
            score += 45; reasons.append(f"Possible domain typo; did you mean {typo_suggestion}?")
    score = min(score, 100)
    risk = "high" if score >= 60 else "medium" if score >= 25 else "low"
    return RiskResult(score, risk, reasons)
