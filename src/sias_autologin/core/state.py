"""Portable portal state observations, distinct from internet connectivity."""
import json
from urllib.parse import urlparse
from .portal import PORTAL_ORIGIN

def authentication_state(status: int, body: bytes, *, portal_origin: str = PORTAL_ORIGIN) -> tuple[str, str]:
    """Classify the verified info interface without retaining personal fields."""
    if status != 200:
        return "unknown", "unexpected_http_status"
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        return "unknown", "invalid_json"
    if not isinstance(payload, dict):
        return "unknown", "unexpected_structure"
    data = payload.get("data")
    if (payload.get("success") is True and isinstance(data, dict)
            and isinstance(data.get("basic"), dict)):
        return "authenticated", "info_basic_present"
    location = payload.get("location")
    if payload.get("success") is False and isinstance(location, str):
        try:
            target = urlparse(location)
            portal = urlparse(portal_origin)
            if (target.scheme == portal.scheme and target.hostname == portal.hostname
                    and (target.port or 80) == (portal.port or 80)
                    and target.path == "/ac_portal/needauth.html"):
                return "auth_required", "info_needauth_location"
        except ValueError:
            pass
    return "unknown", "unexpected_structure"


def query_authentication_state(client) -> tuple[str, str]:
    # A fresh session for each observation; preserve the existing proxy behavior.
    try:
        status, body = client.request(client.build_opener(), client.settings.info_url, data={"opr": "list"})
        return authentication_state(status, body, portal_origin=client.settings.origin)
    except Exception as exc:
        # Error text/response contents can contain identifiers; record only type.
        return "unknown", type(exc).__name__
