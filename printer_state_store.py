"""Small persistent state store for the local Bambu dashboard.

This file stores dashboard-only data:
- custom display names;
- latest merged printer status received from MQTT;
- last updated timestamp.
- local print history detected from MQTT status changes.

It never stores Bambu credentials and never sends anything to Bambu Cloud.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_FILE = Path(__file__).with_name("printer_state_store.json")
_LOCK = threading.Lock()
MAX_COMPLETED_PRINT_JOBS = 5

ACTIVE_PRINT_STATES = {
    "RUNNING",
    "PRINTING",
    "PREPARE",
    "PREPARING",
    "SLICING",
    "PAUSE",
    "PAUSED",
    "HEATING",
    "CALIBRATING",
}

FINISHED_PRINT_STATES = {
    "FINISH",
    "FINISHED",
    "COMPLETED",
    "IDLE",
    "FAILED",
    "FAIL",
    "ERROR",
    "CANCELLED",
    "CANCELED",
    "STOPPED",
}

PRINT_JOB_SIGNAL_FIELDS = {
    "task_id",
    "subtask_name",
    "gcode_file",
    "gcode_state",
    "mc_percent",
    "mc_remaining_time",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_state() -> dict[str, Any]:
    return {"version": 1, "printers": {}}


def _empty_print_history() -> dict[str, Any]:
    return {"active": None, "completed": []}


def _read_state_unlocked() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return empty_state()

    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return empty_state()

    if not isinstance(data, dict):
        return empty_state()
    if not isinstance(data.get("printers"), dict):
        data["printers"] = {}
    data.setdefault("version", 1)
    return data


def _write_state_unlocked(data: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix=STATE_FILE.name + ".",
        suffix=".tmp",
        dir=str(STATE_FILE.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")
        os.replace(temp_name, STATE_FILE)
    finally:
        if os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except OSError:
                pass


def _ensure_print_history_unlocked(record: dict[str, Any]) -> dict[str, Any]:
    history = record.get("print_history")
    if not isinstance(history, dict):
        history = _empty_print_history()
        record["print_history"] = history

    active = history.get("active")
    if active is not None and not isinstance(active, dict):
        history["active"] = None

    completed = history.get("completed")
    if not isinstance(completed, list):
        completed = []
    completed = [deepcopy(job) for job in completed if isinstance(job, dict)]
    history["completed"] = completed[:MAX_COMPLETED_PRINT_JOBS]
    return history


def _ensure_printer_unlocked(
    state: dict[str, Any],
    device_id: str,
    *,
    cloud_name: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    printers = state.setdefault("printers", {})
    record = printers.setdefault(
        device_id,
        {
            "device_id": device_id,
            "custom_display_name": "",
            "cloud_name": cloud_name or "",
            "model": model or "",
            "latest_status": {},
            "last_updated": "",
        },
    )

    record["device_id"] = device_id
    if cloud_name:
        record["cloud_name"] = str(cloud_name)
    if model:
        record["model"] = str(model)
    record.setdefault("custom_display_name", "")
    record.setdefault("latest_status", {})
    record.setdefault("last_updated", "")
    _ensure_print_history_unlocked(record)
    return record


def _normalize_print_state(value: Any) -> str:
    if value in (None, ""):
        return ""
    return str(value).strip().upper()


def _status_file_name(status: dict[str, Any]) -> str:
    value = status.get("subtask_name") or status.get("gcode_file") or ""
    return str(value).strip() if value not in (None, "") else ""


def _status_task_id(status: dict[str, Any]) -> str:
    value = status.get("task_id") or ""
    return str(value).strip() if value not in (None, "") else ""


def _has_print_job_signal(update: dict[str, Any]) -> bool:
    return any(key in update for key in PRINT_JOB_SIGNAL_FIELDS)


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_seconds(start_time: Any, end_time: str) -> int | None:
    start = _parse_iso_datetime(start_time)
    end = _parse_iso_datetime(end_time)
    if start is None or end is None:
        return None
    return max(0, int((end - start).total_seconds()))


def _new_active_print_job(
    *,
    task_id: str,
    file_name: str,
    state: str,
    start_time: str,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "file_name": file_name or "Unknown file",
        "start_time": start_time,
        "end_time": "",
        "duration_seconds": None,
        "result": "",
        "last_state": state,
        "last_seen_time": start_time,
    }


def _same_print_job(active_job: dict[str, Any], task_id: str, file_name: str) -> bool:
    active_task_id = str(active_job.get("task_id") or "").strip()
    active_file_name = str(active_job.get("file_name") or "").strip()

    if active_task_id and task_id:
        return active_task_id == task_id
    if active_file_name and file_name and active_file_name != "Unknown file":
        return active_file_name == file_name
    return True


def _close_active_print_job(history: dict[str, Any], result: str, end_time: str) -> None:
    active_job = history.get("active")
    if not isinstance(active_job, dict):
        history["active"] = None
        return

    completed_job = deepcopy(active_job)
    completed_job["end_time"] = end_time
    completed_job["result"] = result or str(active_job.get("last_state") or "UNKNOWN")
    completed_job["duration_seconds"] = _duration_seconds(
        completed_job.get("start_time"),
        end_time,
    )

    completed = history.get("completed")
    if not isinstance(completed, list):
        completed = []
    completed.insert(0, completed_job)
    history["completed"] = [
        job for job in completed if isinstance(job, dict)
    ][:MAX_COMPLETED_PRINT_JOBS]
    history["active"] = None


def _update_print_history_unlocked(
    record: dict[str, Any],
    *,
    previous_status: dict[str, Any],
    latest_status: dict[str, Any],
    status_update: dict[str, Any],
    timestamp: str,
) -> None:
    del previous_status  # Kept in the signature for future transition-specific rules.

    history = _ensure_print_history_unlocked(record)
    state = _normalize_print_state(latest_status.get("gcode_state"))
    task_id = _status_task_id(latest_status)
    file_name = _status_file_name(latest_status)
    has_job_signal = _has_print_job_signal(status_update)
    is_active = state in ACTIVE_PRINT_STATES
    is_finished = state in FINISHED_PRINT_STATES

    active_job = history.get("active")
    if isinstance(active_job, dict):
        if task_id and not active_job.get("task_id"):
            active_job["task_id"] = task_id
        if file_name and (
            not active_job.get("file_name")
            or active_job.get("file_name") == "Unknown file"
        ):
            active_job["file_name"] = file_name
        if state:
            active_job["last_state"] = state
        active_job["last_seen_time"] = timestamp

        if is_finished:
            _close_active_print_job(history, state, timestamp)
            return

        if is_active and has_job_signal and not _same_print_job(active_job, task_id, file_name):
            _close_active_print_job(
                history,
                str(active_job.get("last_state") or "UNKNOWN"),
                timestamp,
            )
            history["active"] = _new_active_print_job(
                task_id=task_id,
                file_name=file_name,
                state=state,
                start_time=timestamp,
            )
        return

    if is_active and has_job_signal:
        history["active"] = _new_active_print_job(
            task_id=task_id,
            file_name=file_name,
            state=state,
            start_time=timestamp,
        )


def merge_status_dict(existing: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge partial MQTT status without deleting missing keys."""
    merged = deepcopy(existing)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_status_dict(merged[key], value)
        else:
            # If Bambu explicitly sends null, keep it. Only missing keys are ignored.
            merged[key] = deepcopy(value)
    return merged


def ensure_printer(
    device_id: str,
    *,
    cloud_name: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    with _LOCK:
        state = _read_state_unlocked()
        record = _ensure_printer_unlocked(
            state,
            device_id,
            cloud_name=cloud_name,
            model=model,
        )
        _write_state_unlocked(state)
        return deepcopy(record)


def get_printer_record(device_id: str) -> dict[str, Any]:
    with _LOCK:
        state = _read_state_unlocked()
        record = state.get("printers", {}).get(device_id)
        return deepcopy(record) if isinstance(record, dict) else {}


def get_latest_status(device_id: str) -> dict[str, Any]:
    record = get_printer_record(device_id)
    latest_status = record.get("latest_status", {})
    return deepcopy(latest_status) if isinstance(latest_status, dict) else {}


def get_print_history(device_id: str) -> dict[str, Any]:
    record = get_printer_record(device_id)
    history = record.get("print_history")
    if not isinstance(history, dict):
        return _empty_print_history()

    active = history.get("active")
    completed = history.get("completed")
    completed_jobs = (
        [deepcopy(job) for job in completed if isinstance(job, dict)]
        if isinstance(completed, list)
        else []
    )
    return {
        "active": deepcopy(active) if isinstance(active, dict) else None,
        "completed": completed_jobs[:MAX_COMPLETED_PRINT_JOBS],
    }


def get_display_name(device_id: str, fallback: str) -> str:
    record = get_printer_record(device_id)
    for key in ("custom_display_name", "cloud_name"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def set_custom_display_name(device_id: str, display_name: str) -> dict[str, Any]:
    with _LOCK:
        state = _read_state_unlocked()
        record = _ensure_printer_unlocked(state, device_id)
        record["custom_display_name"] = display_name.strip()
        _write_state_unlocked(state)
        return deepcopy(record)


def save_printer_status(
    device_id: str,
    status_update: dict[str, Any],
    *,
    cloud_name: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Merge a partial MQTT print object into the latest known printer status."""
    if not isinstance(status_update, dict):
        status_update = {}

    with _LOCK:
        state = _read_state_unlocked()
        record = _ensure_printer_unlocked(
            state,
            device_id,
            cloud_name=cloud_name,
            model=model,
        )

        previous_status = record.get("latest_status")
        if not isinstance(previous_status, dict):
            previous_status = {}

        # MQTT messages are partial; update only fields present in this message.
        latest_status = merge_status_dict(previous_status, status_update)
        record["latest_status"] = latest_status
        timestamp = utc_now()
        record["last_updated"] = timestamp

        _update_print_history_unlocked(
            record,
            previous_status=previous_status,
            latest_status=latest_status,
            status_update=status_update,
            timestamp=timestamp,
        )

        _write_state_unlocked(state)
        return deepcopy(record)
