"""Canonical client-address resolution for trusted reverse-proxy deployments."""

from __future__ import annotations

import hashlib
import ipaddress


def _address(value: str):
    try:
        return ipaddress.ip_address(str(value).strip())
    except ValueError:
        return None


def _networks(values):
    networks = []
    for value in values or []:
        try:
            networks.append(ipaddress.ip_network(str(value).strip(), strict=False))
        except ValueError:
            continue
    return networks


def _trusted(address, networks) -> bool:
    return bool(address and any(address in network for network in networks))


def resolve_client_ip(remote_addr: str, forwarded_for: str, trusted_proxy_cidrs) -> str:
    """Return the nearest untrusted hop; ignore forwarding from untrusted peers."""

    remote = _address(remote_addr)
    if remote is None:
        return ""
    networks = _networks(trusted_proxy_cidrs)
    if not _trusted(remote, networks):
        return str(remote)
    forwarded = [_address(value) for value in str(forwarded_for or "").split(",")]
    chain = [value for value in forwarded if value is not None] + [remote]
    for address in reversed(chain):
        if not _trusted(address, networks):
            return str(address)
    return str(chain[0]) if chain else str(remote)


def client_ip(request) -> str:
    from django.conf import settings

    trusted = getattr(settings, "TRUSTED_PROXY_CIDRS", []) if getattr(settings, "TRUST_PROXY_HEADERS", False) else []
    return resolve_client_ip(
        request.META.get("REMOTE_ADDR", ""),
        request.META.get("HTTP_X_FORWARDED_FOR", ""),
        trusted,
    )


def client_ip_key(request) -> str:
    from django.conf import settings

    value = client_ip(request)
    return hashlib.sha256((settings.SECRET_KEY + "|client-ip|" + value).encode("utf-8")).hexdigest() if value else "unknown"
