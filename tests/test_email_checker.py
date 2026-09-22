import pytest

from app.services.dns_checker import DnsState, DomainDnsResult
from app.services.email_checker import check_email


@pytest.mark.asyncio
async def test_invalid_email_is_high_risk():
    result = await check_email("not-an-email")
    assert result.valid_format is False
    assert result.risk == "high"


@pytest.mark.asyncio
async def test_disposable_and_role_signals(monkeypatch):
    async def fake_dns(_):
        return DomainDnsResult(DnsState.EXISTS)
    monkeypatch.setattr("app.services.email_checker.check_domain_dns", fake_dns)
    result = await check_email("admin@mailinator.com")
    assert result.disposable and result.role_account
    assert "Disposable email provider" in result.reasons


@pytest.mark.asyncio
@pytest.mark.parametrize("address", ["hello@gmail.com", "person@outlook.com", "person@yahoo.com", "person@proton.me"])
async def test_free_providers_are_low_risk_when_dns_succeeds(monkeypatch, address):
    async def fake_dns(_):
        return DomainDnsResult(DnsState.EXISTS)
    monkeypatch.setattr("app.services.email_checker.check_domain_dns", fake_dns)
    result = await check_email(address)
    assert result.free_provider is True
    assert result.risk == "low" and result.risk_score == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("state", [DnsState.TIMEOUT, DnsState.TEMPORARY_FAILURE, DnsState.RESOLVER_ERROR])
async def test_dns_uncertainty_is_unknown_and_not_high_risk(monkeypatch, state):
    async def fake_dns(_):
        return DomainDnsResult(state)
    monkeypatch.setattr("app.services.email_checker.check_domain_dns", fake_dns)
    result = await check_email("person@outlook.com")
    assert result.domain_exists is None and result.mx_exists is None
    assert result.risk == "low"
    assert "DNS verification temporarily unavailable" in result.reasons


@pytest.mark.asyncio
async def test_typo_disposable_and_nonexistent_signals(monkeypatch):
    async def fake_dns(domain):
        return DomainDnsResult(DnsState.DOES_NOT_EXIST if "does-not-exist" in domain else DnsState.EXISTS)
    monkeypatch.setattr("app.services.email_checker.check_domain_dns", fake_dns)
    assert (await check_email("hello@gmial.com")).typo_suggestion == "gmail.com"
    assert (await check_email("test@guerrillamail.com")).disposable is True
    result = await check_email("hello@this-domain-does-not-exist-928374.com")
    assert result.domain_exists is False and result.risk == "high"
