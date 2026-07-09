"""Monitor all accessible Bambu Cloud printers and print compact status updates"""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
import urllib.error
import urllib.request
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

import printer_state_store

try:
    import requests
except ModuleNotFoundError:
    requests = None  # type: ignore[assignment]


DEFAULT_MQTT_HOST = "us.mqtt.bambulab.com"
DEFAULT_MQTT_PORT = 8883
REQUEST_TIMEOUT_SECONDS = 20
MESSAGE_TIMEOUT_SECONDS = 30

DEVICE_BINDING_ENDPOINTS = (
    (
        "Bambu Cloud device bindings",
        "https://api.bambulab.com/v1/iot-service/api/user/bind",
    ),
)

DEVICE_ID_KEYS = (
    "dev_id",
    "devId",
    "device_id",
    "deviceId",
    "serial",
    "serial_number",
    "serialNumber",
    "sn",
)

WATCHED_FIELDS = (
    "state",
    "percent",
    "remaining_minutes",
    "file_name",
    "task_id",
)

PUSHALL_PAYLOAD = {
    "pushing": {
        "sequence_id": "0",
        "command": "pushall",
        "version": 1,
        "push_target": 1,
    }
}


class ConfigError(ValueError):
    """Raised when required local configuration is missing"""


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    user_id: str
    access_token: str
    debug_mqtt: bool


@dataclass(frozen=True)
class PrinterDevice:
    number: int
    device_id: str
    name: str | None = None
    model: str | None = None


@dataclass(frozen=True)
class PrinterStatus:
    state: Any = None
    percent: Any = None
    remaining_minutes: Any = None
    file_name: Any = None
    task_id: Any = None

    def signature(self) -> tuple[Any, ...]:
        """Only these fields decide whether a new output block is printed"""
        return tuple(getattr(self, field_name) for field_name in WATCHED_FIELDS)

    def has_any_watched_value(self) -> bool:
        """Ignore MQTT reports that do not contain any field we care about"""
        return any(getattr(self, field_name) not in (None, "") for field_name in WATCHED_FIELDS)


def load_config() -> Config:
    """Load secrets/config from .env located beside this script"""
    env_path = Path(__file__).with_name(".env")
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    required = ("BAMBU_USER_ID", "BAMBU_ACCESS_TOKEN")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        raise ConfigError(
            "Missing required value(s): "
            + ", ".join(missing)
            + ". Add them to your local .env file."
        )

    placeholders = [
        name for name in required if os.environ[name].strip().lower() == "replace_me"
    ]
    if placeholders:
        raise ConfigError("Replace placeholder value(s): " + ", ".join(placeholders) + ".")

    host = os.getenv("BAMBU_MQTT_HOST", DEFAULT_MQTT_HOST).strip() or DEFAULT_MQTT_HOST
    port_text = os.getenv("BAMBU_MQTT_PORT", str(DEFAULT_MQTT_PORT)).strip()
    try:
        port = int(port_text)
    except ValueError as error:
        raise ConfigError("BAMBU_MQTT_PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise ConfigError("BAMBU_MQTT_PORT must be between 1 and 65535.")

    debug_mqtt = os.getenv("DEBUG_MQTT", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    return Config(
        host=host,
        port=port,
        user_id=os.environ["BAMBU_USER_ID"].strip(),
        access_token=os.environ["BAMBU_ACCESS_TOKEN"].strip(),
        debug_mqtt=debug_mqtt,
    )


def show_value(value: Any) -> str:
    """Convert missing fields into readable terminal text."""
    if value in (None, ""):
        return "<not received yet>"
    return str(value)


def first_present(data: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value for the provided key names."""
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def walk_objects(value: Any) -> list[dict[str, Any]]:
    """Return every dictionary found inside an arbitrary JSON respon"""
    objects: list[dict[str, Any]] = []
    if isinstance(value, dict):
        objects.append(value)
        for child in value.values():
            objects.extend(walk_objects(child))
    elif isinstance(value, list):
        for child in value:
            objects.extend(walk_objects(child))
    return objects


def extract_device_id(device: dict[str, Any]) -> str | None:
    """Use an identifier returned by the cloud API"""
    value = first_present(device, *DEVICE_ID_KEYS)
    if value is None:
        return None
    return str(value).strip() or None


def extract_devices_from_response(body: Any) -> list[dict[str, Any]]:
    """Find likely printer/device objects in a cloud respon"""
    devices: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for item in walk_objects(body):
        device_id = extract_device_id(item)
        if not device_id or device_id in seen_ids:
            continue
        seen_ids.add(device_id)
        devices.append(item)

    return devices


def get_cloud_json(
    url: str,
    headers: dict[str, str],
) -> tuple[int | None, Any | None, str | None]:
    """GET JSON from Bambu Cloud using requests if available"""
    if requests is not None:
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as error:
            return None, None, str(error)

        try:
            return response.status_code, response.json(), None
        except ValueError:
            return response.status_code, None, "response was not JSON"

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status_code = response.status
            raw_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        status_code = error.code
        raw_body = error.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as error:
        return None, None, str(error.reason)
    except TimeoutError as error:
        return None, None, str(error)

    try:
        return status_code, json.loads(raw_body), None
    except json.JSONDecodeError:
        return status_code, None, "response was not JSON"


def load_cloud_devices(config: Config) -> list[PrinterDevice]:
    """Query Bambu Cloud for devices linked to the account"""
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Accept": "application/json",
        "User-Agent": "bambu-cloud-multi-status-poc/1.0",
    }

    collected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    print("checking cloud devices")
    if requests is None:
        print("requests is not installed; using built-in urllib fallback")

    for label, url in DEVICE_BINDING_ENDPOINTS:
        status_code, body, error = get_cloud_json(url, headers)
        if status_code is None:
            print(f"{label}: request failed: {error}")
            continue

        print(f"{label}: HTTP {status_code}")
        if status_code == 401:
            print("401: access token is invalid, expired, or not accepted by this endpoint.")
            continue
        if status_code == 403:
            print("403: token is recognized but this endpoint is forbidden for this account.")
            continue
        if status_code == 404:
            print("404: device-binding endpoint may have changed or may be unavailable.")
            continue

        if body is None:
            print(f"{label}: {error or 'response was not JSON'}, skipping it.")
            continue

        for device in extract_devices_from_response(body):
            device_id = extract_device_id(device)
            if not device_id or device_id in seen_ids:
                continue
            seen_ids.add(device_id)
            collected.append(device)

    printers: list[PrinterDevice] = []
    for number, device in enumerate(collected, start=1):
        device_id = extract_device_id(device)
        if not device_id:
            continue
        printers.append(
            PrinterDevice(
                number=number,
                device_id=device_id,
                name=first_present(device, "name", "dev_name", "devName", "device_name"),
                model=first_present(
                    device,
                    "model",
                    "dev_model_name",
                    "devModelName",
                    "device_model",
                ),
            )
        )

    return printers


def extract_status(data: Any) -> PrinterStatus:
    """Extract only the fields that should trigger output updates"""
    if not isinstance(data, dict):
        return PrinterStatus()

    print_data = data.get("print")
    if not isinstance(print_data, dict):
        return PrinterStatus()

    file_name = print_data.get("subtask_name") or print_data.get("gcode_file")
    return PrinterStatus(
        state=print_data.get("gcode_state"),
        percent=print_data.get("mc_percent"),
        remaining_minutes=print_data.get("mc_remaining_time"),
        file_name=file_name,
        task_id=print_data.get("task_id"),
    )


def keep_existing_if_missing(previous: Any, current: Any) -> Any:
    """Keep the previous value when a new MQTT report omits a field"""
    if current in (None, ""):
        return previous
    return current


def merge_status(previous: PrinterStatus | None, current: PrinterStatus) -> PrinterStatus:
    """Merge partial MQTT updates without replacing known values with missing ones"""
    if previous is None:
        return current

    return PrinterStatus(
        state=keep_existing_if_missing(previous.state, current.state),
        percent=keep_existing_if_missing(previous.percent, current.percent),
        remaining_minutes=keep_existing_if_missing(
            previous.remaining_minutes,
            current.remaining_minutes,
        ),
        file_name=keep_existing_if_missing(previous.file_name, current.file_name),
        task_id=keep_existing_if_missing(previous.task_id, current.task_id),
    )


class MultiPrinterMonitor:
    """One MQTT client subscribed to all discovered printer report topics"""

    def __init__(
        self,
        config: Config,
        printers: list[PrinterDevice],
        *,
        console_output: bool = True,
    ) -> None:
        self.config = config
        self.printers = printers
        self.console_output = console_output
        self.printer_by_id = {printer.device_id: printer for printer in printers}
        self.topic_to_device_id = {
            f"device/{printer.device_id}/report": printer.device_id for printer in printers
        }
        self.request_topic_by_id = {
            printer.device_id: f"device/{printer.device_id}/request" for printer in printers
        }

        self._lock = threading.Lock()
        self._latest_status: dict[str, PrinterStatus] = {}
        self._latest_status_data: dict[str, dict[str, Any]] = {}
        self._latest_raw_data: dict[str, Any] = {}
        self._latest_signature: dict[str, tuple[Any, ...]] = {}
        self._last_updated: dict[str, str] = {}
        self._received_device_ids: set[str] = set()
        self._subscribed_device_ids: set[str] = set()
        self._subscribe_topics: list[str] = []
        self._timeout_timer: threading.Timer | None = None
        self._stopping = False

        self._load_persisted_state()

        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"bambu-cloud-multi-monitor-{uuid.uuid4().hex}",
            protocol=mqtt.MQTTv311,
        )
        self.client.username_pw_set(f"u_{config.user_id}", config.access_token)
        self.client.tls_set()

        self.client.on_connect = self.on_connect
        self.client.on_subscribe = self.on_subscribe
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        if config.debug_mqtt:
            self.client.on_log = self.on_log

    def _load_persisted_state(self) -> None:
        """Warm the cache from the local JSON store"""
        for printer in self.printers:
            record = printer_state_store.ensure_printer(
                printer.device_id,
                cloud_name=printer.name,
                model=printer.model,
            )
            latest_status = record.get("latest_status", {})
            if not isinstance(latest_status, dict):
                latest_status = {}

            self._latest_status_data[printer.device_id] = deepcopy(latest_status)
            self._latest_raw_data[printer.device_id] = {"print": deepcopy(latest_status)}
            self._last_updated[printer.device_id] = str(record.get("last_updated") or "")

            status = extract_status({"print": latest_status})
            if status.has_any_watched_value():
                self._latest_status[printer.device_id] = status
                self._latest_signature[printer.device_id] = status.signature()

    def on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        connect_flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        if reason_code.is_failure:
            self._print(f"connection failed: {reason_code}")
            client.disconnect()
            return

        self._print("connected")
        self._subscribe_topics = list(self.topic_to_device_id)
        subscriptions = [(topic, 0) for topic in self._subscribe_topics]
        result, _message_id = client.subscribe(subscriptions)
        if result != mqtt.MQTT_ERR_SUCCESS:
            self._print(f"subscribe request failed with MQTT error {result}")
            client.disconnect()

    def on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        message_id: int,
        reason_code_list: Any,
        properties: Any,
    ) -> None:
        accepted_device_ids: list[str] = []

        for index, reason_code in enumerate(reason_code_list):
            topic = self._subscribe_topics[index] if index < len(self._subscribe_topics) else ""
            device_id = self.topic_to_device_id.get(topic)
            printer = self.printer_by_id.get(device_id or "")
            printer_label = (
                f"Printer {printer.number} ({printer.device_id})" if printer else topic
            )

            if reason_code.is_failure:
                self._print(f"subscription rejected for {printer_label}: {reason_code}")
                continue

            if device_id:
                accepted_device_ids.append(device_id)

        with self._lock:
            self._subscribed_device_ids.update(accepted_device_ids)

        if not accepted_device_ids:
            self._print("no printer subscriptions were accepted; stopping")
            client.disconnect()
            return

        self._print(f"subscribed to {len(accepted_device_ids)} printer(s)")
        for device_id in accepted_device_ids:
            self._publish_pushall(device_id)

        self._start_message_timeout()

    def on_message(self, client: mqtt.Client, userdata: Any, message: Any) -> None:
        device_id = self.topic_to_device_id.get(message.topic)
        if not device_id:
            return

        try:
            payload = message.payload.decode("utf-8")
            data = json.loads(payload)
        except UnicodeDecodeError:
            self._print(f"invalid non-UTF-8 message from {device_id}; ignored")
            return
        except json.JSONDecodeError as error:
            self._print(f"invalid JSON message from {device_id}: {error.msg}; ignored")
            return

        print_update = data.get("print")
        if not isinstance(print_update, dict):
            if self.config.debug_mqtt:
                self._print(f"[mqtt debug] ignored message from {device_id}: no print object")
            return

        snapshot: str | None = None
        with self._lock:
            self._received_device_ids.add(device_id)
            if self._timeout_timer is not None:
                self._timeout_timer.cancel()
                self._timeout_timer = None

            printer = self.printer_by_id[device_id]
            record = printer_state_store.save_printer_status(
                device_id,
                print_update,
                cloud_name=printer.name,
                model=printer.model,
            )
            merged_status = record.get("latest_status", {})
            if not isinstance(merged_status, dict):
                merged_status = {}

            self._latest_status_data[device_id] = deepcopy(merged_status)
            self._latest_raw_data[device_id] = {"print": deepcopy(merged_status)}
            self._last_updated[device_id] = str(record.get("last_updated") or "")

            incoming_status = extract_status({"print": merged_status})
            if not incoming_status.has_any_watched_value():
                if self.config.debug_mqtt:
                    self._print(f"[mqtt debug] stored detail-only message from {device_id}")
                return

            status = merge_status(self._latest_status.get(device_id), incoming_status)
            new_signature = status.signature()
            if self._latest_signature.get(device_id) == new_signature:
                return

            self._latest_status[device_id] = status
            self._latest_signature[device_id] = new_signature
            snapshot = self._format_snapshot_locked()

        if snapshot:
            self._print(snapshot)

    def on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        if not self._stopping:
            self._print(f"disconnected: {reason_code}")

    def on_log(self, client: mqtt.Client, userdata: Any, level: int, message: str) -> None:
        safe_message = message.replace(self.config.access_token, "<redacted>")
        safe_message = safe_message.replace(f"u_{self.config.user_id}", "<redacted-user>")
        self._print(f"[mqtt debug] {safe_message}")

    def run(self) -> None:
        self._print(f"connecting to {self.config.host}:{self.config.port} with TLS")
        self.client.connect(self.config.host, self.config.port, keepalive=60)
        self.client.loop_forever()

    def stop(self) -> None:
        with self._lock:
            self._stopping = True
            if self._timeout_timer is not None:
                self._timeout_timer.cancel()
                self._timeout_timer = None
        try:
            self.client.disconnect()
        except mqtt.MQTTException:
            pass

    def _publish_pushall(self, device_id: str) -> None:
        topic = self.request_topic_by_id[device_id]
        payload = json.dumps(PUSHALL_PAYLOAD)
        result = self.client.publish(topic, payload, qos=0)
        printer = self.printer_by_id[device_id]
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            self._print(f"pushall failed for Printer {printer.number} ({device_id}): MQTT {result.rc}")

    def _start_message_timeout(self) -> None:
        with self._lock:
            if self._timeout_timer is not None:
                self._timeout_timer.cancel()
            self._timeout_timer = threading.Timer(
                MESSAGE_TIMEOUT_SECONDS,
                self._print_missing_initial_statuses,
            )
            self._timeout_timer.daemon = True
            self._timeout_timer.start()

    def _print_missing_initial_statuses(self) -> None:
        with self._lock:
            if self._stopping:
                return
            missing = [
                printer
                for printer in self.printers
                if printer.device_id in self._subscribed_device_ids
                and printer.device_id not in self._received_device_ids
            ]

        if missing:
            self._print(
                f"no watched status fields received within {MESSAGE_TIMEOUT_SECONDS} seconds "
                "for: "
                + ", ".join(f"Printer {printer.number} ({printer.device_id})" for printer in missing)
            )

    def _print(self, message: str) -> None:
        """Print only in CLI mode"""
        if not self.console_output:
            return
        stream = sys.stdout
        if stream is None:
            return
        encoding = stream.encoding or "utf-8"
        try:
            stream.write(message + "\n")
            stream.flush()
        except UnicodeEncodeError:
            safe_message = message.encode(encoding, errors="replace").decode(encoding)
            stream.write(safe_message + "\n")
            stream.flush()

    def _format_snapshot_locked(self) -> str:
        """Format all printers as one compact block. Call while holding _lock"""
        lines: list[str] = ["", "Printer status update:"]
        for printer in self.printers:
            status = self._latest_status.get(printer.device_id)
            lines.append(f"Printer {printer.number} ({printer.device_id}):")
            lines.append(f"  State: {show_value(status.state if status else None)}")
            lines.append(f"  Percent: {show_value(status.percent if status else None)}")
            lines.append(
                "  Remaining minutes: "
                + show_value(status.remaining_minutes if status else None)
            )
            lines.append(f"  File name: {show_value(status.file_name if status else None)}")
            lines.append(f"  Task ID: {show_value(status.task_id if status else None)}")
            lines.append("")
        return "\n".join(lines).rstrip()


def print_discovered_printers(printers: list[PrinterDevice]) -> None:
    print(f"found {len(printers)} printer/device id(s)")
    for printer in printers:
        extra: list[str] = []
        if printer.name:
            extra.append(f"name={printer.name}")
        if printer.model:
            extra.append(f"model={printer.model}")
        suffix = " (" + ", ".join(extra) + ")" if extra else ""
        print(f"Printer {printer.number} ({printer.device_id}){suffix}")


def main() -> int:
    try:
        config = load_config()
    except ConfigError as error:
        print(f"configuration error: {error}", file=sys.stderr)
        return 2

    printers = load_cloud_devices(config)
    if not printers:
        print(
            "no printer/device ids were found from the cloud device-binding endpoint; "
            "cannot build MQTT topics"
        )
        return 3

    print_discovered_printers(printers)

    monitor = MultiPrinterMonitor(config, printers)
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nCtrl+C received; disconnecting gracefully")
        monitor.stop()
    except (OSError, mqtt.MQTTException) as error:
        print(f"MQTT connection error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
