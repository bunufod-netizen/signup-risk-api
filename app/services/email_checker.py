from email_validator import EmailNotValidError, validate_email

from app.schemas import CheckResponse
from app.services.dns_checker import check_domain_dns
from app.services.domain_lists import FREE_PROVIDERS, ROLE_LOCAL_PARTS, TYPO_SUGGESTIONS, is_disposable
from app.services.risk_engine import calculate_risk


async def check_email(email: str) -> CheckResponse:
    raw_email = email.strip()
    try:
        validated = validate_email(raw_email, check_deliverability=False)
    except EmailNotValidError:
        risk = calculate_risk(valid_format=False, domain_exists=None, mx_exists=None, dns_uncertain=False, disposable=False, role_account=False, typo_suggestion=None)
        return CheckResponse(email=raw_email, valid_format=False, domain=None, domain_exists=None, mx_exists=None, disposable=False, role_account=False, free_provider=False, typo_suggestion=None, risk=risk.risk, risk_score=risk.score, reasons=risk.reasons)

    normalized = validated.normalized
    local_part, domain = normalized.rsplit("@", 1)
    domain = domain.lower()
    dns = await check_domain_dns(domain)
    disposable = is_disposable(domain)
    role_account = local_part.lower() in ROLE_LOCAL_PARTS
    typo_suggestion = TYPO_SUGGESTIONS.get(domain)
    risk = calculate_risk(valid_format=True, domain_exists=dns.exists, mx_exists=dns.mx_exists, dns_uncertain=dns.is_uncertain, disposable=disposable, role_account=role_account, typo_suggestion=typo_suggestion)
    return CheckResponse(email=normalized, valid_format=True, domain=domain, domain_exists=dns.exists, mx_exists=dns.mx_exists, disposable=disposable, role_account=role_account, free_provider=domain in FREE_PROVIDERS, typo_suggestion=typo_suggestion, risk=risk.risk, risk_score=risk.score, reasons=risk.reasons)
