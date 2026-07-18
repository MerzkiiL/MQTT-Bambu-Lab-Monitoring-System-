<<<<<<< HEAD
"""Local desktop dashboard for Bambu Cloud printer statuses."""
=======
"""Local dashboard for Bambu Cloud printer statuses"""
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Callable

import streamlit as st

try:
    import webview
except ModuleNotFoundError:
    webview = None  # type: ignore[assignment]

import printer_state_store
from bambu_cloud_multi_status import (
    ConfigError,
    MultiPrinterMonitor,
    PrinterDevice,
    PrinterStatus,
    load_cloud_devices,
    load_config,
)


DEFAULT_DASHBOARD_PORT = 8502
PRINTER_REFRESH_SECONDS = 10
SELECTED_PRINTER_STATE_KEY = "selected_printer_id"
<<<<<<< HEAD
LANGUAGE_STATE_KEY = "ui_language"
SIDEBAR_OPEN_STATE_KEY = "sidebar_open"
DETAILS_SECTION_STATE_KEY = "details_section"

TRANSLATIONS = {
    "RUS": {
        "local_monitor": "Локальный MQTT-монитор",
        "printers": "Принтеры",
        "running": "работает",
        "stopped": "остановлен",
        "total_printers": "Всего принтеров",
        "waiting_devices": "Ожидание принтеров из облака...",
        "details": "Детали",
        "choose_printer": "Выбери принтер слева или нажми «Детали» на карточке.",
        "last_updated": "Обновлено",
        "dashboard_name": "Название в dashboard",
        "save_name": "Сохранить имя",
        "name_saved": "Имя сохранено",
        "main": "Основное",
        "history": "Журнал",
        "no_printer_data": "Данные по этому принтеру ещё не получены.",
        "all_printer_data": "Все данные принтера",
        "no_fields": "Нет доступных полей.",
        "full_json": "Полный JSON",
        "history_empty": "Журнал пока пуст",
        "last_refresh": "Последнее обновление UI",
        "waiting": "Ожидание",
        "unknown_model": "Модель неизвестна",
        "unknown_file": "Файл неизвестен",
        "percent": "Процент",
        "remaining": "Осталось",
        "file_name": "Имя файла",
        "parameter": "Параметр",
        "value": "Значение",
        "field": "Поле",
        "file": "Файл",
        "start": "Начало",
        "end": "Конец",
        "print_time": "Время печати",
        "result": "Результат",
        "task_id": "ID задачи",
        "in_progress": "В процессе",
        "status": "Статус",
        "progress": "Прогресс",
        "remaining_minutes": "Осталось минут",
        "nozzle_temp": "Темп. сопла",
        "nozzle_target": "Цель сопла",
        "bed_temp": "Темп. стола",
        "bed_target": "Цель стола",
        "chamber_temp": "Темп. камеры",
        "wifi_signal": "Wi-Fi сигнал",
        "cooling_fan": "Скорость вентилятора",
        "fan_1": "Вентилятор 1",
        "fan_2": "Вентилятор 2",
        "errors": "Ошибки",
        "hms_errors": "Ошибки HMS",
        "layer": "Слой",
        "total_layers": "Всего слоёв",
        "ams_status": "AMS",
        "printer": "Принтер",
        "open_menu": "Открыть меню",
        "close_menu": "Закрыть меню",
    },
    "ENG": {
        "local_monitor": "Local MQTT monitor",
        "printers": "Printers",
        "running": "running",
        "stopped": "stopped",
        "total_printers": "Total printers",
        "waiting_devices": "Waiting for cloud printers...",
        "details": "Details",
        "choose_printer": "Choose a printer in the sidebar or click Details on its card.",
        "last_updated": "Last updated",
        "dashboard_name": "Dashboard name",
        "save_name": "Save name",
        "name_saved": "Name saved",
        "main": "Overview",
        "history": "History",
        "no_printer_data": "No data has been received for this printer yet.",
        "all_printer_data": "All printer data",
        "no_fields": "No fields are available.",
        "full_json": "Full JSON",
        "history_empty": "Print history is empty",
        "last_refresh": "Last UI refresh",
        "waiting": "Waiting",
        "unknown_model": "Unknown model",
        "unknown_file": "Unknown file",
        "percent": "Percent",
        "remaining": "Remaining",
        "file_name": "File name",
        "parameter": "Parameter",
        "value": "Value",
        "field": "Field",
        "file": "File",
        "start": "Start",
        "end": "End",
        "print_time": "Print duration",
        "result": "Result",
        "task_id": "Task ID",
        "in_progress": "In progress",
        "status": "Status",
        "progress": "Progress",
        "remaining_minutes": "Remaining minutes",
        "nozzle_temp": "Nozzle temp.",
        "nozzle_target": "Nozzle target",
        "bed_temp": "Bed temp.",
        "bed_target": "Bed target",
        "chamber_temp": "Chamber temp.",
        "wifi_signal": "Wi-Fi signal",
        "cooling_fan": "Cooling fan speed",
        "fan_1": "Fan 1",
        "fan_2": "Fan 2",
        "errors": "Errors",
        "hms_errors": "HMS errors",
        "layer": "Layer",
        "total_layers": "Total layers",
        "ams_status": "AMS",
        "printer": "Printer",
        "open_menu": "Open menu",
        "close_menu": "Close menu",
    },
}

KNOWN_LABEL_KEYS = {
    "gcode_state": "status",
    "mc_percent": "progress",
    "mc_remaining_time": "remaining_minutes",
    "subtask_name": "file",
    "gcode_file": "file",
    "task_id": "task_id",
    "nozzle_temper": "nozzle_temp",
    "nozzle_target_temper": "nozzle_target",
    "bed_temper": "bed_temp",
    "bed_target_temper": "bed_target",
    "chamber_temper": "chamber_temp",
    "wifi_signal": "wifi_signal",
    "cooling_fan_speed": "cooling_fan",
    "big_fan1_speed": "fan_1",
    "big_fan2_speed": "fan_2",
    "print_error": "errors",
    "hms": "hms_errors",
    "hms_list": "hms_errors",
    "layer_num": "layer",
    "total_layer_num": "total_layers",
    "ams_status": "ams_status",
    "ams": "ams_status",
=======

KNOWN_LABELS = {
    "gcode_state": "Статус",
    "mc_percent": "Прогресс",
    "mc_remaining_time": "Осталось минут",
    "subtask_name": "Файл",
    "gcode_file": "Файл",
    "task_id": "ID задачи",
    "nozzle_temper": "Темп. сопла",
    "nozzle_target_temper": "Цель сопла",
    "bed_temper": "Темп. стола",
    "bed_target_temper": "Цель стола",
    "chamber_temper": "Темп. камеры",
    "wifi_signal": "Wi-Fi сигнал",
    "cooling_fan_speed": "Скорость вентилятора",
    "big_fan1_speed": "Вентилятор 1",
    "big_fan2_speed": "Вентилятор 2",
    "print_error": "Ошибки",
    "hms": "Ошибки HMS",
    "hms_list": "Ошибки HMS",
    "layer_num": "Слой",
    "total_layer_num": "Всего слоёв",
    "ams_status": "AMS",
    "ams": "AMS",
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
}

IMPORTANT_FIELDS = (
    "gcode_state",
    "mc_percent",
    "mc_remaining_time",
    "subtask_name",
    "gcode_file",
    "task_id",
    "nozzle_temper",
    "bed_temper",
    "wifi_signal",
    "cooling_fan_speed",
    "big_fan1_speed",
    "big_fan2_speed",
    "print_error",
    "layer_num",
    "total_layer_num",
    "ams_status",
)


def configure_utf8_stdio() -> None:
    """Avoid Windows charmap crashes when Streamlit/pywebview has no real console."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


configure_utf8_stdio()


<<<<<<< HEAD
def initialize_ui_state() -> None:
    """Initialize UI-only state once per Streamlit session."""
    if st.session_state.get(LANGUAGE_STATE_KEY) not in TRANSLATIONS:
        st.session_state[LANGUAGE_STATE_KEY] = "RUS"
    if SIDEBAR_OPEN_STATE_KEY not in st.session_state:
        st.session_state[SIDEBAR_OPEN_STATE_KEY] = True
    if st.session_state.get(DETAILS_SECTION_STATE_KEY) not in {"main", "history"}:
        st.session_state[DETAILS_SECTION_STATE_KEY] = "main"


def current_language() -> str:
    """Return the selected UI language without affecting monitor state."""
    language = str(st.session_state.get(LANGUAGE_STATE_KEY, "RUS")).upper()
    return language if language in TRANSLATIONS else "RUS"


def tr(key: str) -> str:
    """Translate a UI label using the current Streamlit session language."""
    language = current_language()
    return TRANSLATIONS.get(language, TRANSLATIONS["RUS"]).get(key, key)


=======
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
@dataclass
class PrinterSnapshot:
    printer: PrinterDevice
    status: PrinterStatus | None
    status_data: dict[str, Any]
    last_updated: str
    display_name: str


class DashboardRuntime:
    """Owns the background MQTT monitor used by the Streamlit dashboard."""

    def __init__(self) -> None:
        self.error: str | None = None
<<<<<<< HEAD
=======
        self.started_at = time.time()
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        self.monitor_thread: threading.Thread | None = None
        self.monitor: MultiPrinterMonitor | None = None
        self.printers: list[PrinterDevice] = []
        self.stopped = False
        self._start()

    def _start(self) -> None:
        self.stopped = False
        try:
            config = load_config()
            self.printers = load_cloud_devices(config)
            if not self.printers:
                self.error = (
                    "No printer/device IDs were found from Bambu Cloud. "
                    "Check internet, token, account, and Bambu Cloud availability."
                )
                return

            for printer in self.printers:
                printer_state_store.ensure_printer(
                    printer.device_id,
                    cloud_name=printer.name,
                    model=printer.model,
                )

            self.monitor = MultiPrinterMonitor(
                config,
                self.printers,
                console_output=False,
            )
            self.monitor_thread = threading.Thread(
                target=self._run_monitor,
                name="bambu-cloud-mqtt-monitor",
                daemon=True,
            )
            self.monitor_thread.start()
        except ConfigError as error:
            self.error = f"Configuration error: {error}"
        except Exception as error:
            self.error = f"Startup error: {error}"

    def _run_monitor(self) -> None:
        if self.monitor is None:
            return
        try:
            self.monitor.run()
        except Exception as error:
            if not self.stopped:
                self.error = f"MQTT monitor stopped: {error}"

    def snapshots(self) -> list[PrinterSnapshot]:
        snapshots: list[PrinterSnapshot] = []

        if self.monitor is None:
            for printer in self.printers:
                record = printer_state_store.get_printer_record(printer.device_id)
                status_data = record.get("latest_status", {})
                if not isinstance(status_data, dict):
                    status_data = {}
                display_name = printer_state_store.get_display_name(
                    printer.device_id,
                    fallback_printer_name(printer),
                )
                snapshots.append(
                    PrinterSnapshot(
                        printer=printer,
                        status=None,
                        status_data=deepcopy(status_data),
                        last_updated=str(record.get("last_updated") or ""),
                        display_name=display_name,
                    )
                )
            return snapshots

        with self.monitor._lock:
            for printer in self.printers:
                record = printer_state_store.get_printer_record(printer.device_id)
                display_name = printer_state_store.get_display_name(
                    printer.device_id,
                    fallback_printer_name(printer),
                )
                status_data = self.monitor._latest_status_data.get(printer.device_id)
                if not isinstance(status_data, dict):
                    status_data = record.get("latest_status", {})
                if not isinstance(status_data, dict):
                    status_data = {}

                snapshots.append(
                    PrinterSnapshot(
                        printer=printer,
                        status=deepcopy(self.monitor._latest_status.get(printer.device_id)),
                        status_data=deepcopy(status_data),
                        last_updated=str(
                            self.monitor._last_updated.get(printer.device_id)
                            or record.get("last_updated")
                            or ""
                        ),
                        display_name=display_name,
                    )
                )
        return snapshots

    def is_monitor_alive(self) -> bool:
        return not self.stopped and bool(self.monitor_thread and self.monitor_thread.is_alive())

    def start(self) -> None:
        if self.is_monitor_alive():
            return
        self.error = None
<<<<<<< HEAD
=======
        self.started_at = time.time()
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        self.monitor_thread = None
        self.monitor = None
        self.printers = []
        self.stopped = False
        self._start()

    def stop(self) -> None:
        self.stopped = True
        if self.monitor is not None:
            self.monitor.stop()


@st.cache_resource
def get_runtime() -> DashboardRuntime:
    return DashboardRuntime()


def fallback_printer_name(printer: PrinterDevice) -> str:
    if printer.name:
        return str(printer.name)
<<<<<<< HEAD
    return f"{tr('printer')} {printer.number}"
=======
    return f"Printer {printer.number}"
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7


def display_value(value: Any) -> str:
    if value in (None, ""):
<<<<<<< HEAD
        return tr("waiting")
=======
        return "Waiting"
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
    return str(value)


def format_remaining_minutes(value: Any) -> str:
    if value in (None, ""):
<<<<<<< HEAD
        return tr("waiting")
=======
        return "Waiting"
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
    try:
        minutes = int(float(value))
    except (TypeError, ValueError):
        return str(value)
    hours, mins = divmod(minutes, 60)
    if hours:
<<<<<<< HEAD
        return f"{hours}h {mins}m" if current_language() == "ENG" else f"{hours}ч {mins}м"
    return f"{mins}m" if current_language() == "ENG" else f"{mins}м"
=======
        return f"{hours}ч {mins}м"
    return f"{mins}м"
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7


def parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_history_time(value: Any) -> str:
    parsed = parse_iso_datetime(value)
    if parsed is None:
        return str(value) if value not in (None, "") else "—"
    return parsed.astimezone().strftime("%Y-%m-%d %H:%M")


def duration_between(start_time: Any, end_time: Any) -> int | None:
    start = parse_iso_datetime(start_time)
    end = parse_iso_datetime(end_time)
    if start is None or end is None:
        return None
    return max(0, int((end - start).total_seconds()))


def format_duration_seconds(value: Any) -> str:
    if value in (None, ""):
        return "—"
    try:
        total_seconds = max(0, int(float(value)))
    except (TypeError, ValueError):
        return str(value)
    total_minutes = max(0, round(total_seconds / 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
<<<<<<< HEAD
        return f"{hours}h {minutes:02d}m" if current_language() == "ENG" else f"{hours}ч {minutes:02d}м"
    return f"{minutes}m" if current_language() == "ENG" else f"{minutes}м"
=======
        return f"{hours}ч {minutes:02d}м"
    return f"{minutes}м"
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7


def format_field_value(key: str, value: Any) -> str:
    if value in (None, ""):
        return "—"

    key_lower = key.lower()
    if key_lower in {"mc_percent"}:
        return f"{value}%"
    if key_lower in {"mc_remaining_time"}:
        return format_remaining_minutes(value)
    if "temper" in key_lower or "temperature" in key_lower:
        try:
            return f"{float(value):.1f} °C"
        except (TypeError, ValueError):
            return f"{value} °C"
    if "fan" in key_lower and "speed" in key_lower:
        return f"{value}%"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def status_css_class(state: Any) -> str:
    normalized = display_value(state).upper()
    if normalized in {"RUNNING", "PRINTING"}:
        return "status-running"
    if normalized in {"IDLE", "FINISH", "FINISHED", "COMPLETED"}:
        return "status-finished"
    if normalized in {"PAUSE", "PAUSED"}:
        return "status-paused"
    if normalized in {"FAILED", "ERROR"}:
        return "status-error"
    return "status-waiting"


def label_for_key(path: str) -> str:
    key = path.split(".")[-1]
<<<<<<< HEAD
    if key in KNOWN_LABEL_KEYS:
        return tr(KNOWN_LABEL_KEYS[key])
    if "hms" in path.lower() or "error" in key.lower():
        return tr("errors")
=======
    if key in KNOWN_LABELS:
        return KNOWN_LABELS[key]
    if "hms" in path.lower() or "error" in key.lower():
        return "Ошибки"
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
    if "ams" in path.lower():
        return "AMS"
    return path


def flatten_status(value: Any, path: str = "") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            rows.extend(flatten_status(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            rows.extend(flatten_status(child, child_path))
    else:
        rows.append(
            {
<<<<<<< HEAD
                tr("parameter"): label_for_key(path),
                tr("value"): format_field_value(path.split(".")[-1], value),
                tr("field"): path,
=======
                "Параметр": label_for_key(path),
                "Значение": format_field_value(path.split(".")[-1], value),
                "Поле": path,
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
            }
        )
    return rows


def important_rows(status_data: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    used_labels: set[str] = set()

    file_value = status_data.get("subtask_name") or status_data.get("gcode_file")
    if file_value not in (None, ""):
<<<<<<< HEAD
        rows.append({tr("parameter"): tr("file"), tr("value"): format_field_value("subtask_name", file_value)})
        used_labels.add(tr("file"))
=======
        rows.append({"Параметр": "Файл", "Значение": format_field_value("subtask_name", file_value)})
        used_labels.add("Файл")
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7

    for key in IMPORTANT_FIELDS:
        if key in {"subtask_name", "gcode_file"}:
            continue
        if key not in status_data:
            continue
        label = label_for_key(key)
        if label in used_labels:
            continue
<<<<<<< HEAD
        rows.append({tr("parameter"): label, tr("value"): format_field_value(key, status_data[key])})
=======
        rows.append({"Параметр": label, "Значение": format_field_value(key, status_data[key])})
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        used_labels.add(label)

    # Include common nested/variant fields if present.
    for row in flatten_status(status_data):
<<<<<<< HEAD
        path_lower = row[tr("field")].lower()
        label = row[tr("parameter")]
        if label in used_labels:
            continue
        if any(word in path_lower for word in ("hms", "error", "ams")):
            rows.append({tr("parameter"): label, tr("value"): row[tr("value")]})
=======
        path_lower = row["Поле"].lower()
        label = row["Параметр"]
        if label in used_labels:
            continue
        if any(word in path_lower for word in ("hms", "error", "ams")):
            rows.append({"Параметр": label, "Значение": row["Значение"]})
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
            used_labels.add(label)

    return rows


def selected_printer_id() -> str | None:
    session_value = st.session_state.get(SELECTED_PRINTER_STATE_KEY)
    if session_value:
        return str(session_value)

    value = st.query_params.get("selected_printer")
    if isinstance(value, list):
        value = value[0] if value else None
    if value:
        st.session_state[SELECTED_PRINTER_STATE_KEY] = value
    return value


def select_printer(device_id: str) -> None:
    st.session_state[SELECTED_PRINTER_STATE_KEY] = device_id
    st.query_params["selected_printer"] = device_id


def inject_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --soft-border: rgba(15, 23, 42, 0.10);
            --muted: #64748b;
<<<<<<< HEAD
=======
            --panel: #ffffff;
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
            --bg: #f7f9fc;
        }

        .stApp {
            background: var(--bg);
            color: #0f172a;
        }

        section.main > div.block-container {
            max-width: 100%;
            padding-top: 1.2rem;
            padding-left: 1.35rem;
            padding-right: 1.35rem;
            overflow-x: hidden;
        }

        #MainMenu, footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        .stDeployButton {
            display: none !important;
            visibility: hidden !important;
        }

        header,
        [data-testid="stHeader"] {
            background: transparent !important;
            height: 0 !important;
            min-height: 0 !important;
            pointer-events: none;
        }

<<<<<<< HEAD
        .st-key-sidebar_toggle {
            position: fixed !important;
            top: 12px !important;
            left: 12px !important;
            z-index: 999999 !important;
            width: 42px !important;
        }

        .st-key-sidebar_toggle button {
            width: 42px !important;
            height: 42px !important;
            min-height: 42px !important;
            padding: 0 !important;
            background: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid rgba(15, 23, 42, 0.14) !important;
            border-radius: 12px !important;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.10) !important;
            font-size: 1.15rem !important;
        }

        .st-key-dashboard_sidebar {
            position: sticky;
            top: 12px;
        }

        .st-key-dashboard_sidebar [data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff;
            border-right: 1px solid var(--soft-border);
            border-radius: 18px;
        }

        .st-key-dashboard_sidebar [data-testid="stMarkdownContainer"] h1 {
=======
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            display: flex !important;
            visibility: visible !important;
            pointer-events: auto !important;
            z-index: 999999 !important;
        }

        [data-testid="collapsedControl"] {
            position: fixed !important;
            top: 12px !important;
            left: 12px !important;
            background: #ffffff !important;
            border: 1px solid rgba(15, 23, 42, 0.14) !important;
            border-radius: 12px !important;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.10) !important;
        }

        section[data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--soft-border);
            min-width: 238px !important;
            width: 252px !important;
        }

        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
            font-size: 1.45rem;
            margin-bottom: 0.25rem;
        }

<<<<<<< HEAD
        .st-key-ui_language [data-testid="stButtonGroup"] {
            float: right;
            width: fit-content;
        }

        .st-key-ui_language [data-baseweb="button-group"],
        .st-key-details_section [data-baseweb="button-group"] {
            overflow: hidden;
            gap: 0 !important;
            padding: 2px;
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.12);
            border-radius: 10px;
        }

        .st-key-ui_language button[kind="segmented_control"],
        .st-key-ui_language button[kind="segmented_controlActive"],
        .st-key-details_section button[kind="segmented_control"],
        .st-key-details_section button[kind="segmented_controlActive"] {
            min-height: 32px !important;
            padding: 0.35rem 0.85rem !important;
            border: 0 !important;
            border-radius: 7px !important;
            box-shadow: none !important;
            font-weight: 700 !important;
        }

        .st-key-ui_language button[kind="segmented_control"],
        .st-key-details_section button[kind="segmented_control"] {
            background: #ffffff !important;
            color: #64748b !important;
        }

        .st-key-ui_language button[kind="segmented_controlActive"],
        .st-key-details_section button[kind="segmented_controlActive"] {
            background: rgba(239, 68, 68, 0.10) !important;
            color: #dc2626 !important;
        }

        .st-key-ui_language button p,
        .st-key-details_section button p {
            color: inherit !important;
        }

        .st-key-ui_language [data-testid="stWidgetLabel"],
        .st-key-details_section [data-testid="stWidgetLabel"] {
            display: none !important;
        }

=======
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        .main-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 18px;
        }

        .main-title h1 {
            font-size: 2rem;
            line-height: 1.15;
            margin: 0;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 7px 12px;
            font-size: 0.85rem;
            font-weight: 800;
            text-transform: uppercase;
            border: 1px solid transparent;
        }

        .monitor-running {
            background: rgba(34, 197, 94, 0.13);
            color: rgb(22, 163, 74);
            border-color: rgba(34, 197, 94, 0.28);
        }

        .monitor-stopped {
            background: rgba(239, 68, 68, 0.12);
            color: rgb(220, 38, 38);
            border-color: rgba(239, 68, 68, 0.24);
        }

        .stat-card {
            background: #ffffff;
            border: 1px solid var(--soft-border);
            border-radius: 16px;
            padding: 14px 16px;
            margin-bottom: 18px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.035);
        }

<<<<<<< HEAD
=======
        .detail-panel {
            background: #ffffff;
            border: 1px solid var(--soft-border);
            border-radius: 20px;
            padding: 18px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.045);
        }

        .detail-panel h2 {
            font-size: 1.35rem;
            margin: 0 0 2px 0;
        }

        .muted {
            color: var(--muted);
            font-size: 0.9rem;
        }

>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        main div[data-testid="column"] {
            min-width: 0;
            padding-top: 6px;
        }

        .printer-card-body {
            min-height: 245px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            padding: 12px;
            margin: -4px -4px 10px -4px;
            border: 1px solid transparent;
            border-radius: 16px;
            background: transparent;
        }

        .printer-card-body.printer-card-selected {
            border-color: rgba(239, 68, 68, 0.38);
            background: rgba(239, 68, 68, 0.035);
        }

        .printer-card-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
        }

        .printer-card-title {
            font-size: 1.25rem;
            line-height: 1.2;
            font-weight: 850;
            color: #0f172a;
            word-break: break-word;
        }

        .printer-card-model {
            margin-top: 5px;
            color: var(--muted);
            font-size: 0.88rem;
            word-break: break-word;
        }

        .printer-status-badge {
            flex: 0 0 auto;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.75rem;
            font-weight: 850;
            letter-spacing: 0.02em;
            border: 1px solid transparent;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .printer-status-badge.status-running {
            background: rgba(34, 197, 94, 0.13);
            color: rgb(22, 163, 74);
            border-color: rgba(34, 197, 94, 0.28);
        }

        .printer-status-badge.status-finished {
            background: rgba(59, 130, 246, 0.12);
            color: rgb(37, 99, 235);
            border-color: rgba(59, 130, 246, 0.24);
        }

        .printer-status-badge.status-paused {
            background: rgba(245, 158, 11, 0.16);
            color: rgb(180, 83, 9);
            border-color: rgba(245, 158, 11, 0.28);
        }

        .printer-status-badge.status-error {
            background: rgba(239, 68, 68, 0.13);
            color: rgb(220, 38, 38);
            border-color: rgba(239, 68, 68, 0.28);
        }

        .printer-status-badge.status-waiting {
            background: rgba(100, 116, 139, 0.12);
            color: rgb(71, 85, 105);
            border-color: rgba(100, 116, 139, 0.20);
        }

        .printer-metrics {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .printer-metric {
            background: #f8fafc;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 14px;
            padding: 10px 12px;
            min-width: 0;
        }

        .printer-metric-label {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .printer-metric-value {
            color: #0f172a;
            font-size: 1.12rem;
            font-weight: 850;
            word-break: break-word;
        }

        .printer-file {
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 14px;
            padding: 10px 12px;
            min-width: 0;
        }

        .printer-file-label {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .printer-file-value {
            color: #0f172a;
            font-size: 0.96rem;
            font-weight: 700;
            line-height: 1.3;
            word-break: break-word;
        }

        main div[data-testid="stButton"] > button,
        main div[data-testid="stFormSubmitButton"] > button {
            min-height: 0 !important;
            height: auto !important;
            padding: 0.55rem 0.85rem !important;
            border-radius: 0.75rem !important;
            border: 1px solid rgba(15, 23, 42, 0.12) !important;
            background: #ffffff !important;
            color: #0f172a !important;
            box-shadow: none !important;
            text-align: center !important;
            justify-content: center !important;
            cursor: pointer !important;
        }

        main div[data-testid="stButton"] > button:hover,
        main div[data-testid="stFormSubmitButton"] > button:hover {
            border-color: rgba(59, 130, 246, 0.55) !important;
            background: rgba(59, 130, 246, 0.045) !important;
        }

        main div[data-testid="stButton"] > button[kind="primary"] {
            background: #ef4444 !important;
            color: #ffffff !important;
            border-color: #ef4444 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def card_html(snapshot: PrinterSnapshot, selected: bool) -> str:
    status = snapshot.status
    status_text = display_value(status.state if status else snapshot.status_data.get("gcode_state"))
    percent = display_value(
        status.percent if status and status.percent not in (None, "") else snapshot.status_data.get("mc_percent")
    )
    remaining = format_remaining_minutes(
        status.remaining_minutes
        if status and status.remaining_minutes not in (None, "")
        else snapshot.status_data.get("mc_remaining_time")
    )
    file_name = display_value(
        status.file_name
        if status and status.file_name not in (None, "")
        else snapshot.status_data.get("subtask_name") or snapshot.status_data.get("gcode_file")
    )
    model = snapshot.printer.model or snapshot.status_data.get("printer_type") or ""

<<<<<<< HEAD
    percent_text = tr("waiting") if percent == tr("waiting") else f"{percent}%"
    status_text = status_text.upper()
    status_class = status_css_class(status_text)
    model_text = str(model) if model else tr("unknown_model")
=======
    percent_text = "Waiting" if percent == "Waiting" else f"{percent}%"
    status_text = status_text.upper()
    status_class = status_css_class(status_text)
    model_text = str(model) if model else "Unknown model"
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
    selected_class = " printer-card-selected" if selected else ""

    return f"""
        <div class="printer-card-body{selected_class}">
          <div class="printer-card-head">
            <div>
              <div class="printer-card-title">{escape(snapshot.display_name)}</div>
              <div class="printer-card-model">{escape(model_text)}</div>
            </div>
            <span class="printer-status-badge {status_class}">{escape(status_text)}</span>
          </div>

          <div class="printer-metrics">
            <div class="printer-metric">
<<<<<<< HEAD
              <div class="printer-metric-label">{escape(tr("percent"))}</div>
              <div class="printer-metric-value">{escape(percent_text)}</div>
            </div>
            <div class="printer-metric">
              <div class="printer-metric-label">{escape(tr("remaining"))}</div>
=======
              <div class="printer-metric-label">Percent</div>
              <div class="printer-metric-value">{escape(percent_text)}</div>
            </div>
            <div class="printer-metric">
              <div class="printer-metric-label">Remaining</div>
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
              <div class="printer-metric-value">{escape(remaining)}</div>
            </div>
          </div>

          <div class="printer-file">
<<<<<<< HEAD
            <div class="printer-file-label">{escape(tr("file_name"))}</div>
=======
            <div class="printer-file-label">File name</div>
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
            <div class="printer-file-value">{escape(file_name)}</div>
          </div>
        </div>
    """


<<<<<<< HEAD
def render_language_toggle() -> None:
    """Render the persistent language selection as a compact segment group."""
    _, switch = st.columns([10, 1.35], gap="small")
    with switch:
        st.segmented_control(
            "Language",
            options=("RUS", "ENG"),
            format_func=lambda language: "RU" if language == "RUS" else "ENG",
            key=LANGUAGE_STATE_KEY,
            required=True,
            label_visibility="collapsed",
            width="content",
        )


def toggle_sidebar() -> None:
    """Toggle only UI layout state; cached runtime and printer selection survive."""
    st.session_state[SIDEBAR_OPEN_STATE_KEY] = not st.session_state[SIDEBAR_OPEN_STATE_KEY]


def render_sidebar_toggle() -> None:
    is_open = bool(st.session_state[SIDEBAR_OPEN_STATE_KEY])
    st.button(
        "☰",
        key="sidebar_toggle",
        help=tr("close_menu") if is_open else tr("open_menu"),
        on_click=toggle_sidebar,
    )


def render_sidebar(runtime: DashboardRuntime, snapshots: list[PrinterSnapshot], selected_id: str | None) -> None:
    with st.container(border=True, key="dashboard_sidebar"):
        st.markdown("# Bambu Cloud")
        st.caption(tr("local_monitor"))
=======
def render_sidebar(runtime: DashboardRuntime, snapshots: list[PrinterSnapshot], selected_id: str | None) -> None:
    with st.sidebar:
        st.markdown("# Bambu Cloud")
        st.caption("Local MQTT monitor")
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7

        running = runtime.is_monitor_alive()
        button_label = "STOP" if running else "START"
        button_type = "primary" if running else "secondary"
        if st.button(button_label, type=button_type, use_container_width=True):
            if running:
                runtime.stop()
            else:
                runtime.start()
            st.rerun()

        st.markdown("---")
<<<<<<< HEAD
        st.caption(tr("printers"))
=======
        st.caption("Printers")
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        for snapshot in snapshots:
            selected = snapshot.printer.device_id == selected_id
            label = f"▸ {snapshot.display_name}" if selected else snapshot.display_name
            st.button(
                label,
                key=f"sidebar_printer_{snapshot.printer.device_id}",
                type="primary" if selected else "secondary",
                use_container_width=True,
                on_click=select_printer,
                args=(snapshot.printer.device_id,),
            )


def render_header(runtime: DashboardRuntime, snapshots: list[PrinterSnapshot]) -> None:
    running = runtime.is_monitor_alive()
    badge_class = "monitor-running" if running else "monitor-stopped"
<<<<<<< HEAD
    badge_text = tr("running") if running else tr("stopped")
=======
    badge_text = "running" if running else "stopped"
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
    st.markdown(
        f"""
        <div class="main-title">
          <h1>MQTT Monitor</h1>
          <span class="status-pill {badge_class}">{badge_text}</span>
        </div>
        <div class="stat-card">
<<<<<<< HEAD
          <b>{escape(tr("total_printers"))}:</b> {len(snapshots)}
=======
          <b>Total printers:</b> {len(snapshots)}
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        </div>
        """,
        unsafe_allow_html=True,
    )
    if runtime.error:
        st.error(runtime.error)


def render_cards(snapshots: list[PrinterSnapshot], selected_id: str | None) -> None:
    if not snapshots:
<<<<<<< HEAD
        st.info(tr("waiting_devices"))
=======
        st.info("Waiting for cloud devices...")
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        return

    columns_per_row = 2
    for start in range(0, len(snapshots), columns_per_row):
        columns = st.columns(columns_per_row)
        for column, snapshot in zip(columns, snapshots[start : start + columns_per_row]):
            with column:
                selected = snapshot.printer.device_id == selected_id
                with st.container(border=True):
                    st.markdown(card_html(snapshot, selected), unsafe_allow_html=True)
                    st.button(
<<<<<<< HEAD
                        tr("details"),
=======
                        "Details",
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
                        key=f"details_button_{snapshot.printer.device_id}",
                        type="primary" if selected else "secondary",
                        use_container_width=True,
                        on_click=select_printer,
                        args=(snapshot.printer.device_id,),
                    )


def selected_snapshot(snapshots: list[PrinterSnapshot], selected_id: str | None) -> PrinterSnapshot | None:
    if selected_id:
        for snapshot in snapshots:
            if snapshot.printer.device_id == selected_id:
                return snapshot
    return snapshots[0] if snapshots else None


def save_rename(snapshot: PrinterSnapshot, new_name: str) -> None:
    printer_state_store.set_custom_display_name(snapshot.printer.device_id, new_name)
<<<<<<< HEAD
    st.success(tr("name_saved"))
=======
    st.success("Имя сохранено")
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
    st.rerun()


def history_job_rows(device_id: str) -> list[dict[str, str]]:
    history = printer_state_store.get_print_history(device_id)
    rows: list[dict[str, str]] = []

    active = history.get("active")
    if isinstance(active, dict):
        rows.append(
            {
<<<<<<< HEAD
                tr("file"): str(active.get("file_name") or tr("unknown_file")),
                tr("start"): format_history_time(active.get("start_time")),
                tr("end"): "—",
                tr("print_time"): tr("in_progress"),
                tr("result"): tr("in_progress"),
                tr("task_id"): str(active.get("task_id") or "—"),
=======
                "Файл": str(active.get("file_name") or "Unknown file"),
                "Начало": format_history_time(active.get("start_time")),
                "Конец": "—",
                "Время печати": "В процессе",
                "Результат": "В процессе",
                "ID задачи": str(active.get("task_id") or "—"),
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
            }
        )

    completed = history.get("completed")
    if isinstance(completed, list):
        for job in completed[:5]:
            if not isinstance(job, dict):
                continue
            duration = job.get("duration_seconds")
            if duration in (None, ""):
                duration = duration_between(job.get("start_time"), job.get("end_time"))
            rows.append(
                {
<<<<<<< HEAD
                    tr("file"): str(job.get("file_name") or tr("unknown_file")),
                    tr("start"): format_history_time(job.get("start_time")),
                    tr("end"): format_history_time(job.get("end_time")),
                    tr("print_time"): format_duration_seconds(duration),
                    tr("result"): str(job.get("result") or "—"),
                    tr("task_id"): str(job.get("task_id") or "—"),
=======
                    "Файл": str(job.get("file_name") or "Unknown file"),
                    "Начало": format_history_time(job.get("start_time")),
                    "Конец": format_history_time(job.get("end_time")),
                    "Время печати": format_duration_seconds(duration),
                    "Результат": str(job.get("result") or "—"),
                    "ID задачи": str(job.get("task_id") or "—"),
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
                }
            )

    return rows


def render_print_history(snapshot: PrinterSnapshot) -> None:
    rows = history_job_rows(snapshot.printer.device_id)
    if not rows:
<<<<<<< HEAD
        st.info(tr("history_empty"))
=======
        st.info("Журнал пока пуст")
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        return

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        height=min(360, 42 + len(rows) * 38),
    )


def render_details(snapshot: PrinterSnapshot | None) -> None:
    if snapshot is None:
        with st.container(border=True):
<<<<<<< HEAD
            st.subheader(tr("details"))
            st.caption(tr("choose_printer"))
=======
            st.subheader("Детали")
            st.caption("Выбери принтер слева или нажми Details на карточке.")
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
        return

    with st.container(border=True):
        st.subheader(snapshot.display_name)
        model = snapshot.printer.model or snapshot.status_data.get("printer_type") or ""
        if model:
            st.caption(str(model))
        if snapshot.last_updated:
<<<<<<< HEAD
            st.caption(f"{tr('last_updated')}: {snapshot.last_updated}")

        with st.form(key=f"rename_form_{snapshot.printer.device_id}", clear_on_submit=False):
            new_name = st.text_input(tr("dashboard_name"), value=snapshot.display_name)
            if st.form_submit_button(tr("save_name"), use_container_width=True):
                save_rename(snapshot, new_name)

        status_data = snapshot.status_data
        details_section = st.segmented_control(
            "Details section",
            options=("main", "history"),
            format_func=lambda section: tr(section),
            key=DETAILS_SECTION_STATE_KEY,
            required=True,
            label_visibility="collapsed",
            width="stretch",
        )

        if details_section == "main":
            if not status_data:
                st.info(tr("no_printer_data"))
=======
            st.caption(f"Last updated: {snapshot.last_updated}")

        with st.form(key=f"rename_form_{snapshot.printer.device_id}", clear_on_submit=False):
            new_name = st.text_input("Название в dashboard", value=snapshot.display_name)
            if st.form_submit_button("Сохранить имя", use_container_width=True):
                save_rename(snapshot, new_name)

        status_data = snapshot.status_data
        main_tab, history_tab = st.tabs(["Основное", "Журнал"])

        with main_tab:
            if not status_data:
                st.info("Данные по этому принтеру ещё не получены.")
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
            else:
                rows = important_rows(status_data)
                if rows:
                    st.dataframe(
                        rows,
                        use_container_width=True,
                        hide_index=True,
                        height=min(420, 42 + len(rows) * 36),
                    )

                all_rows = flatten_status(status_data)
<<<<<<< HEAD
                st.markdown(f"### {tr('all_printer_data')}")
                if all_rows:
                    st.dataframe(all_rows, use_container_width=True, hide_index=True, height=420)
                else:
                    st.info(tr("no_fields"))

                with st.expander(tr("full_json")):
=======
                st.markdown("### Все данные принтера")
                if all_rows:
                    st.dataframe(all_rows, use_container_width=True, hide_index=True, height=420)
                else:
                    st.info("Нет доступных полей.")

                with st.expander("Полный JSON"):
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
                    st.code(
                        json.dumps({"print": status_data}, indent=2, ensure_ascii=False, sort_keys=True),
                        language="json",
                    )
<<<<<<< HEAD
        else:
=======

        with history_tab:
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
            render_print_history(snapshot)


def ten_second_fragment(function: Callable[..., Any]) -> Callable[..., Any]:
    fragment = getattr(st, "fragment", None)
    if callable(fragment):
        return fragment(run_every=f"{PRINTER_REFRESH_SECONDS}s")(function)
    return function


def render_dashboard_body(runtime: DashboardRuntime) -> None:
    snapshots = runtime.snapshots()
    selected_id = selected_printer_id()
    if selected_id is None and snapshots:
        selected_id = snapshots[0].printer.device_id

    render_header(runtime, snapshots)

    main_col, details_col = st.columns([2, 1], gap="large")
    with main_col:
        render_cards(snapshots, selected_id)
    with details_col:
        render_details(selected_snapshot(snapshots, selected_id))

<<<<<<< HEAD
    st.caption(f"{tr('last_refresh')}: " + time.strftime("%Y-%m-%d %H:%M:%S"))
=======
    st.caption("Last UI refresh: " + time.strftime("%Y-%m-%d %H:%M:%S"))
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7


@ten_second_fragment
def render_live_body(runtime: DashboardRuntime) -> None:
<<<<<<< HEAD
=======
    # Important: do not call st.sidebar inside st.fragment.
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7
    render_dashboard_body(runtime)


def streamlit_app() -> None:
    st.set_page_config(
        page_title="Bambu Cloud Printer Dashboard",
        layout="wide",
        menu_items={},
    )
<<<<<<< HEAD
    initialize_ui_state()
    inject_style()
    render_sidebar_toggle()
    render_language_toggle()

    runtime = get_runtime()
    body_renderer = render_dashboard_body if runtime.stopped else render_live_body

    if st.session_state[SIDEBAR_OPEN_STATE_KEY]:
        sidebar_column, body_column = st.columns([1, 4.2], gap="large")
        with sidebar_column:
            sidebar_snapshots = runtime.snapshots()
            sidebar_selected_id = selected_printer_id()
            if sidebar_selected_id is None and sidebar_snapshots:
                sidebar_selected_id = sidebar_snapshots[0].printer.device_id
            render_sidebar(runtime, sidebar_snapshots, sidebar_selected_id)
        with body_column:
            body_renderer(runtime)
    else:
        body_renderer(runtime)
=======
    inject_style()

    runtime = get_runtime()
    sidebar_snapshots = runtime.snapshots()
    sidebar_selected_id = selected_printer_id()
    if sidebar_selected_id is None and sidebar_snapshots:
        sidebar_selected_id = sidebar_snapshots[0].printer.device_id
    render_sidebar(runtime, sidebar_snapshots, sidebar_selected_id)

    if runtime.stopped:
        render_dashboard_body(runtime)
    else:
        render_live_body(runtime)
>>>>>>> b698e7854c83e444ba14c4590b216179e4eb9db7


def running_inside_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def wait_for_port(port: int, timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def launch_desktop_app() -> int:
    if webview is None:
        print(
            "pywebview is not installed. Install dependencies first:\n"
            "  python -m pip install -r requirements.txt"
        )
        return 2

    port = int(os.getenv("BAMBU_DASHBOARD_PORT", str(DEFAULT_DASHBOARD_PORT)))
    app_path = Path(__file__).resolve()
    env = os.environ.copy()
    env["BAMBU_STREAMLIT_CHILD"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.runOnSave=false",
    ]

    process = subprocess.Popen(command, env=env)
    try:
        if not wait_for_port(port):
            print("Streamlit did not start in time. Check the terminal output above.")
            return 1

        webview.create_window(
            "Bambu Cloud Printer Dashboard",
            f"http://127.0.0.1:{port}",
            width=1180,
            height=780,
            min_size=(980, 650),
        )
        webview.start()
        return 0
    finally:
        process.terminate()


if running_inside_streamlit() or os.getenv("BAMBU_STREAMLIT_CHILD") == "1":
    streamlit_app()
elif __name__ == "__main__":
    raise SystemExit(launch_desktop_app())
