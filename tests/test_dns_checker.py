import dns.exception
import dns.resolver
import pytest

from app.services import dns_checker
from app.services.dns_checker import DnsState


class FakeResolver:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.timeout = self.lifetime = None

    def resolve(self, *_):
        outcome = next(self.outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.mark.parametrize(("outcomes", "expected"), [
    ([object()], DnsState.EXISTS),
    ([dns.resolver.NXDOMAIN()], DnsState.DOES_NOT_EXIST),
    ([dns.resolver.NoAnswer(), object()], DnsState.NO_MX),
    ([dns.resolver.NoAnswer(), dns.resolver.NoAnswer()], DnsState.NO_MX),
    ([dns.resolver.LifetimeTimeout()], DnsState.TIMEOUT),
    ([dns.resolver.NoNameservers()], DnsState.TEMPORARY_FAILURE),
    ([dns.exception.DNSException()], DnsState.RESOLVER_ERROR),
])
def test_dns_states(monkeypatch, outcomes, expected):
    monkeypatch.setattr(dns_checker, "_resolver", lambda: FakeResolver(outcomes))
    monkeypatch.setattr(dns_checker.get_settings(), "dns_retries", 0)
    assert dns_checker._lookup_domain("outlook.com").state is expected


def test_temporary_failure_is_retried(monkeypatch):
    calls = 0
    def lookup_once(_):
        nonlocal calls
        calls += 1
        return dns_checker.DomainDnsResult(DnsState.TEMPORARY_FAILURE if calls == 1 else DnsState.EXISTS)
    monkeypatch.setattr(dns_checker, "_lookup_once", lookup_once)
    monkeypatch.setattr(dns_checker.get_settings(), "dns_retries", 1)
    assert dns_checker._lookup_domain("outlook.com").state is DnsState.EXISTS
    assert calls == 2
