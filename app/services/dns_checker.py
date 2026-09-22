import asyncio
from dataclasses import dataclass
from enum import StrEnum

import dns.exception
import dns.resolver

from app.config import get_settings


class DnsState(StrEnum):
    EXISTS = "exists"
    DOES_NOT_EXIST = "does_not_exist"
    NO_MX = "no_mx"
    TIMEOUT = "timeout"
    TEMPORARY_FAILURE = "temporary_failure"
    RESOLVER_ERROR = "resolver_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DomainDnsResult:
    state: DnsState

    @property
    def exists(self) -> bool | None:
        if self.state in (DnsState.EXISTS, DnsState.NO_MX): return True
        if self.state is DnsState.DOES_NOT_EXIST: return False
        return None

    @property
    def mx_exists(self) -> bool | None:
        if self.state is DnsState.EXISTS: return True
        if self.state is DnsState.NO_MX: return False
        return None

    @property
    def is_uncertain(self) -> bool:
        return self.state in {DnsState.TIMEOUT, DnsState.TEMPORARY_FAILURE, DnsState.RESOLVER_ERROR, DnsState.UNKNOWN}


def _resolver() -> dns.resolver.Resolver:
    timeout = get_settings().dns_timeout_seconds
    resolver = dns.resolver.Resolver(configure=True)
    resolver.timeout = timeout
    resolver.lifetime = timeout
    return resolver


def _classify_exception(exc: dns.exception.DNSException) -> DnsState:
    if isinstance(exc, (dns.resolver.LifetimeTimeout, dns.exception.Timeout)):
        return DnsState.TIMEOUT
    if isinstance(exc, dns.resolver.NoNameservers):
        return DnsState.TEMPORARY_FAILURE
    return DnsState.RESOLVER_ERROR


def _lookup_once(domain: str) -> DomainDnsResult:
    resolver = _resolver()
    try:
        resolver.resolve(domain, "MX")
        return DomainDnsResult(DnsState.EXISTS)
    except dns.resolver.NoAnswer:
        # A domain with A/AAAA records still exists even when it has no MX record.
        try:
            resolver.resolve(domain, "A")
            return DomainDnsResult(DnsState.NO_MX)
        except dns.resolver.NXDOMAIN:
            return DomainDnsResult(DnsState.DOES_NOT_EXIST)
        except dns.resolver.NoAnswer:
            return DomainDnsResult(DnsState.NO_MX)
        except dns.exception.DNSException as exc:
            return DomainDnsResult(_classify_exception(exc))
    except dns.resolver.NXDOMAIN:
        return DomainDnsResult(DnsState.DOES_NOT_EXIST)
    except dns.exception.DNSException as exc:
        return DomainDnsResult(_classify_exception(exc))


def _lookup_domain(domain: str) -> DomainDnsResult:
    retries = max(0, get_settings().dns_retries)
    result = DomainDnsResult(DnsState.UNKNOWN)
    for _ in range(retries + 1):
        result = _lookup_once(domain)
        if not result.is_uncertain:
            return result
    return result


async def check_domain_dns(domain: str) -> DomainDnsResult:
    return await asyncio.to_thread(_lookup_domain, domain)
