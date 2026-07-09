# Bambu Cloud Printer Dashboard

Local read-only dashboard for monitoring multiple Bambu Lab printers through community-documented Bambu Cloud MQTT behavior.

This is an experimental proof of concept. It is **not an official Bambu Lab public API** and can break if Bambu changes their cloud API.

The app is designed for Bambu Cloud mode, not LAN-only mode. It does not send printer control commands such as start, stop, pause, or resume.

## Features

- Discovers printers linked to your Bambu account.
- Connects to Bambu Cloud MQTT with TLS.
- Monitors multiple printers.
- Keeps latest known values when MQTT sends partial updates.
- Shows printer cards and a details panel.
- Supports local custom printer names.
- Shows all currently known printer data.
- Tracks local print history:
  - current active print job;
  - last 5 completed jobs per printer.
- Runs as a local Streamlit dashboard and can open in a desktop window through pywebview.

## Files safe to publish

Commit these files:

```text
app.py
bambu_cloud_devices.py
bambu_cloud_multi_status.py
printer_state_store.py
launch_app.pyw
requirements.txt
.env.example
.gitignore
README.md
```

Optional:

```text
bambu/
```

Do **not** commit these:

```text
.env
.venv/
__pycache__/
printer_state_store.json
logs/
*.log
```

`printer_state_store.json` contains local printer IDs, custom names, latest status, and print history. It is ignored by Git and should stay private.

## Setup

Use Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a local `.env` file:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```dotenv
BAMBU_MQTT_HOST=us.mqtt.bambulab.com
BAMBU_MQTT_PORT=8883
BAMBU_USER_ID=replace_me
BAMBU_ACCESS_TOKEN=replace_me
DEBUG_MQTT=false
BAMBU_DASHBOARD_PORT=8502
```

Never commit real `.env` values.

## Run

Desktop app:

```powershell
python app.py
```

Or use:

```powershell
python launch_app.pyw
```

Direct Streamlit mode:

```powershell
streamlit run app.py
```

## Notes

- The dashboard sends `pushall` after subscribing to each printer topic.
- It does not repeatedly send `pushall` every refresh.
- UI refresh does not send printer commands.
- Print history is calculated locally from observed MQTT state changes, so old prints from before the app was running cannot be reconstructed automatically.

## Security

- Keep `.env` private.
- Do not publish access tokens, user IDs, device IDs, or debug logs.
- Check `git status` before pushing.
- If you want a clean public copy, delete `printer_state_store.json` before publishing.
