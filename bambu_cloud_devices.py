"""List Bambu Cloud device bindings using community-documented HTTP endpoints.

This is an experimental, read-only diagnostic script. Bambu Lab does not publish
these endpoints as a stable public API; paths and response formats may change.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv


REQUEST_TIMEOUT_SECONDS = 20

# The first endpoint is the community-documented Bambu Cloud device-binding API.
# The two account endpoints are useful diagnostics for a token that does not
# return devices. They may return 404/403 as the cloud API changes.
ENDPOINTS = (
    (
        "Bambu Cloud device bindings",
        "https://api.bambulab.com/v1/iot-service/api/user/bind",
    ),
    (
        "Bambu Cloud account profile (diagnostic)",
        "https://api.bambulab.com/v1/user-service/my/profile",
    ),
    (
        "MakerWorld account profile (diagnostic)",
        "https://makerworld.com/api/v1/user/profile",
    ),
)

IDENTIFIER_KEYS = {
    "dev_id",
    "devId",
    "device_id",
    "deviceId",
    "serial",
    "serial_number",
    "serialNumber",
    "sn",
}


class ConfigurationError(ValueError):
    """Raised when the required local cloud token is unavailable."""


def load_access_token() -> str:
    """Load BAMBU_ACCESS_TOKEN without printing or persisting it."""
    script_env = Path(__file__).with_name(".env")
    if script_env.exists():
        load_dotenv(script_env)
    else:
        # Allows running the script from a project directory with an existing .env.
        load_dotenv()

    token = os.getenv("BAMBU_ACCESS_TOKEN", "").strip()
    if not token or token.lower() == "replace_me":
        raise ConfigurationError(
            "BAMBU_ACCESS_TOKEN is missing. Add it to a local .env file; do not "
            "paste it into the script or commit it."
        )
    return token


def redact(value: Any, token: str) -> Any:
    """Remove an exact token occurrence if an endpoint echoes it in its response."""
    if isinstance(value, str):
        return value.replace(token, "<redacted>")
    if isinstance(value, list):
        return [redact(item, token) for item in value]
    if isinstance(value, dict):
        return {key: redact(item, token) for key, item in value.items()}
    return value


def print_response_body(response: requests.Response, token: str) -> Any:
    """Print JSON in readable form, or a safe text diagnostic for non-JSON bodies."""
    try:
        body = response.json()
    except ValueError:
        print("Raw response is not JSON:")
        print(redact(response.text, token))
        return None

    safe_body = redact(body, token)
    print("Raw JSON response:")
    print(json.dumps(safe_body, indent=2, ensure_ascii=False, sort_keys=True))
    return body


def show_http_error(status_code: int) -> None:
    """Explain the most actionable HTTP failures without exposing credentials."""
    if status_code == 401:
        print("401: the access token is missing, invalid, expired, or not accepted here.")
    elif status_code == 403:
        print("403: the token was recognized but does not have permission for this endpoint.")
    elif status_code == 404:
        print("404: this community-documented endpoint may have changed or is unavailable.")


def walk_objects(value: Any) -> Iterable[dict[str, Any]]:
    """Yield every dictionary in an arbitrary JSON document."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_objects(child)


def first_present(data: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty matching field, retaining valid zero values."""
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return "<not present>"


def extract_devices(body: Any) -> list[dict[str, Any]]:
    """Find likely device objects without inventing identifiers or topic names."""
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in walk_objects(body):
        if not IDENTIFIER_KEYS.intersection(item):
            continue
        fingerprint = json.dumps(item, sort_keys=True, default=str)
        if fingerprint not in seen:
            seen.add(fingerprint)
            candidates.append(item)
    return candidates


def print_devices(devices: list[dict[str, Any]]) -> None:
    """Show useful fields exactly as returned; do not guess a MQTT topic ID."""
    if not devices:
        print("No device/printer object with a likely identifier was found in this response.")
        return

    print(f"\nLikely devices/printers found: {len(devices)}")
    for number, device in enumerate(devices, start=1):
        print(f"\nDevice {number}:")
        print(f"  Name: {first_present(device, 'name', 'dev_name', 'devName', 'device_name')}")
        print(f"  Model: {first_present(device, 'model', 'dev_model_name', 'devModelName', 'device_model')}")
        print(f"  dev_id: {first_present(device, 'dev_id', 'devId')}")
        print(f"  device_id: {first_present(device, 'device_id', 'deviceId')}")
        print(
            "  Serial: "
            + str(
                first_present(
                    device,
                    'serial',
                    'serial_number',
                    'serialNumber',
                    'sn',
                )
            )
        )
        print(
            "  Online status: "
            + str(
                first_present(
                    device,
                    'online',
                    'is_online',
                    'isOnline',
                    'online_status',
                    'onlineStatus',
                    'status',
                )
            )
        )
        print("  Available keys: " + ", ".join(sorted(device.keys())))


def query_endpoint(session: requests.Session, label: str, url: str, token: str) -> None:
    """Call one endpoint and always display its status and response diagnostic."""
    print("\n" + "=" * 72)
    print(label)
    print(f"GET {url}")

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as error:
        print(f"Request failed: {error}")
        return

    print(f"HTTP status: {response.status_code}")
    body = print_response_body(response, token)
    show_http_error(response.status_code)
    if body is not None:
        print_devices(extract_devices(body))


def main() -> int:
    try:
        token = load_access_token()
    except ConfigurationError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2

    # Do not enable requests debug logging: it could include Authorization headers.
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "bambu-cloud-devices-poc/1.0",
        }
    )

    for label, url in ENDPOINTS:
        query_endpoint(session, label, url, token)

    print("\nDone. Inspect identifiers returned by the device-binding response manually.")
    print("This script intentionally does not build or guess MQTT topic IDs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
