# goe-ocpp-bridge

Isolierte Python-Bridge fuer einen go-eCharger mit lokaler HTTP API. Die Bridge steuert die Wallbox lokal per HTTP und meldet sich gegenueber einem externen Backend als einfacher OCPP 1.6 JSON Charge Point ueber WebSocket.

Home Assistant wird nicht verwendet, nicht veraendert und nicht kontaktiert. Es gibt keine HA-Tokens, keine HA-API-Aufrufe und keine Aenderungen an HA-Konfigurationen.

## Voraussetzungen

- Python 3.10 oder neuer
- Netzwerkzugriff auf die go-e Wallbox
- OCPP 1.6 JSON WebSocket-Backend
- Windows PowerShell oder Linux Shell

## Funktionen

- BootNotification
- Heartbeat
- StatusNotification
- MeterValues
- RemoteStartTransaction
- RemoteStopTransaction
- StartTransaction und StopTransaction passend zu RemoteStart/RemoteStop
- WebSocket-Keepalive und automatischer Reconnect
- Dry-Run-Modus fuer sichere Tests
- Read-only-Modus fuer reine Telemetrie
- Persistenter Status in `state.json`
- Logging auf Konsole und optional in Datei

## Installation unter Windows

```powershell
cd goe-ocpp-bridge
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1
notepad config.yaml
.\run_windows.ps1
```

Falls `python` auf Windows auf eine falsche Version zeigt, nutze den Python-Launcher explizit:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows.ps1 -Python py -PythonArgs "-3.12"
```

Das Installationsscript erstellt eine virtuelle Umgebung in `.venv`, installiert die Abhaengigkeiten und legt `config.yaml` aus `config.example.yaml` an, falls noch keine existiert.

## Installation unter Linux

```bash
cd goe-ocpp-bridge
chmod +x install_linux.sh run_linux.sh
./install_linux.sh
nano config.yaml
./run_linux.sh
```

Optional kann ein bestimmter Python-Interpreter gesetzt werden:

```bash
PYTHON_BIN=python3.12 ./install_linux.sh
```

## Konfiguration

Die Beispielkonfiguration startet absichtlich sicher:

```yaml
bridge:
  dry_run: true
  read_only: true
  allow_remote_start: false
  allow_remote_stop: true
```

Mindestens diese Werte muessen angepasst werden:

```yaml
goe:
  host: "192.168.178.50"

ocpp:
  backend_url: "wss://example.com/ocpp/goe-test-001"
  charge_point_id: "goe-test-001"
```

Die vollstaendige Dokumentation aller Felder steht in [CONFIG.md](CONFIG.md).

## Betrieb

Windows:

```powershell
.\run_windows.ps1 -Config .\config.yaml
```

Linux:

```bash
./run_linux.sh ./config.yaml
```

Die Bridge laeuft im Vordergrund und loggt auf die Konsole. Wenn `bridge.log_file` gesetzt ist, wird zusaetzlich in diese Datei geschrieben.

## Sicherer Testablauf

1. Mit `dry_run: true` und `read_only: true` starten.
2. Im OCPP-Backend pruefen, ob BootNotification, Heartbeat, StatusNotification und MeterValues ankommen.
3. Wenn die Messwerte passen, `read_only: false` setzen.
4. Fuer echte Steuerung `dry_run: false` setzen.
5. `allow_remote_start` und `allow_remote_stop` bewusst freigeben.

RemoteStart wird nur ausgefuehrt, wenn `dry_run: false`, `read_only: false` und `allow_remote_start: true` gesetzt sind. RemoteStop wird nur ausgefuehrt, wenn `dry_run: false`, `read_only: false` und `allow_remote_stop: true` gesetzt sind.

## Messwerte

Fuer alte go-eCharger mit API v1 werden die Einheiten der lokalen API umgerechnet:

- `eto`: Gesamtzaehler in `0.1 kWh`, wird als OCPP Register in Wh gesendet.
- `dws`: Session-Energie in Dezawattsekunden, wird mit `dws / 360` zu Wh.
- `nrg[11]`: Gesamtleistung in `0.01 kW`, wird mit `* 10` zu W.
- `nrg[4..6]`: Strom je Phase in `0.1 A`, wird mit `/ 10` zu A.

Waehrend einer aktiven OCPP-Transaktion wird der OCPP-Registerwert aus `eto` beim Transaktionsstart plus der seitdem gestiegenen `dws`-Session-Energie gebildet. Dadurch steigt der Backend-Zaehler live mit.

## Tests

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Linux:

```bash
.venv/bin/python -m pytest
```

## Projektstruktur

```text
goe-ocpp-bridge/
  README.md
  CONFIG.md
  requirements.txt
  pyproject.toml
  config.example.yaml
  install_windows.ps1
  install_linux.sh
  run_windows.ps1
  run_linux.sh
  src/goe_ocpp_bridge/
  tests/
```

## Weitergabe

Zum Weitergeben reicht der Projektordner ohne lokale Laufzeitdateien. Nicht mitgeben:

- `.venv/`
- `config.yaml`
- `state.json`
- `bridge.log`
- `__pycache__/`
- `*.egg-info/`

Diese Dateien sind in `.gitignore` eingetragen.
