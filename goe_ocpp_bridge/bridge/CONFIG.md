# config.yaml

Die Bridge liest ihre Einstellungen aus `config.yaml`. Beim Installieren wird automatisch eine lokale `config.yaml` aus `config.example.yaml` erstellt, falls noch keine vorhanden ist.

Die Datei enthaelt drei Bereiche:

- `goe`: Verbindung zur go-e Wallbox
- `ocpp`: Verbindung zum OCPP-Backend
- `bridge`: Laufzeit-, Sicherheits- und Logging-Verhalten

## Beispiel

```yaml
goe:
  host: "192.168.178.50"
  api_version: "auto"
  timeout_seconds: 5
  poll_interval_seconds: 30

ocpp:
  version: "1.6"
  backend_url: "wss://example.com/ocpp/goe-test-001"
  charge_point_id: "goe-test-001"
  connector_id: 1
  basic_auth_user: ""
  basic_auth_password: ""

bridge:
  dry_run: true
  read_only: true
  allow_remote_start: false
  allow_remote_stop: true
  heartbeat_interval_seconds: 30
  meter_interval_seconds: 30
  reconnect_interval_seconds: 10
  websocket_ping_interval_seconds: 15
  websocket_ping_timeout_seconds: 20
  log_level: "DEBUG"
  state_file: "state.json"
  log_file: "bridge.log"
```

## goe

`host`

IP-Adresse oder Hostname der go-e Wallbox im lokalen Netzwerk. Ein Schema ist optional. Diese Werte sind gleichwertig:

```yaml
host: "192.168.178.50"
host: "http://192.168.178.50"
```

`api_version`

Welche lokale HTTP API genutzt wird.

- `auto`: Erst API v2 unter `/api/status` testen, sonst API v1 unter `/status` verwenden.
- `v1`: Alte API fest verwenden.
- `v2`: Neue API fest verwenden.

Fuer alte go-eCharger ist meistens `auto` oder `v1` richtig.

`timeout_seconds`

HTTP-Timeout fuer einzelne Abfragen oder Steuerbefehle an die Wallbox.

`poll_interval_seconds`

Reserviert fuer go-e Polling. Aktuell steuert `bridge.meter_interval_seconds`, wie oft Messwerte abgefragt und an OCPP gesendet werden.

## ocpp

`version`

Muss aktuell `1.6` sein. Die Bridge implementiert OCPP 1.6 JSON ueber WebSocket.

`backend_url`

Die vollstaendige WebSocket-URL des OCPP-Backends. Die Bridge verwendet diese URL exakt so, wie sie hier steht.

Beispiel:

```yaml
backend_url: "wss://stromnachbar.de/ocpp/test-go-e-66h8ec"
```

`charge_point_id`

Die Charge-Point-ID, unter der die Bridge im Backend erscheint. Sie muss zum Backend passen. Oft ist sie auch Teil der URL.

`connector_id`

Connector-ID fuer die Wallbox. Fuer diesen Use Case ist normalerweise `1` richtig.

`basic_auth_user` und `basic_auth_password`

Optionale HTTP Basic Auth fuer die WebSocket-Verbindung zum OCPP-Backend. Leer lassen, wenn das Backend keine Basic Auth erwartet.

## bridge

`dry_run`

Wenn `true`, sendet die Bridge keine Start- oder Stop-Kommandos an den go-e. Eingehende RemoteStartTransaction und RemoteStopTransaction werden geloggt und sicher blockiert. Messwerte, Status, BootNotification und Heartbeat werden weiterhin gesendet.

Empfohlen fuer die erste Inbetriebnahme:

```yaml
dry_run: true
```

`read_only`

Wenn `true`, laeuft die Bridge im reinen Lesemodus. Sie sendet nur BootNotification, Heartbeat, StatusNotification und MeterValues. RemoteStartTransaction und RemoteStopTransaction werden blockiert.

`allow_remote_start`

Sicherheitsfreigabe fuer RemoteStartTransaction. Ein RemoteStart wird nur ausgefuehrt, wenn alle drei Bedingungen erfuellt sind:

```yaml
dry_run: false
read_only: false
allow_remote_start: true
```

`allow_remote_stop`

Sicherheitsfreigabe fuer RemoteStopTransaction. Ein RemoteStop wird nur ausgefuehrt, wenn `dry_run: false`, `read_only: false` und `allow_remote_stop: true` gesetzt sind.

`heartbeat_interval_seconds`

Fallback-Intervall fuer OCPP Heartbeat. Wenn das Backend in der BootNotification-Antwort ein eigenes Intervall vorgibt, wird dieses Backend-Intervall verwendet.

`meter_interval_seconds`

Intervall fuer StatusNotification und MeterValues. Bei `15` werden ca. alle 15 Sekunden neue Werte vom go-e gelesen und an das Backend gesendet.

`reconnect_interval_seconds`

Wartezeit vor einem erneuten Verbindungsaufbau, wenn die OCPP-WebSocket-Verbindung beendet wird oder die Bridge einen Fehler abfaengt.

`websocket_ping_interval_seconds`

Technisches WebSocket-Keepalive-Intervall. Das ist zusaetzlich zum OCPP Heartbeat und hilft Backends, Proxies oder Firewalls, die Verbindung offen zu halten.

`websocket_ping_timeout_seconds`

Zeit, die auf eine WebSocket-Pong-Antwort gewartet wird, bevor die Verbindung als defekt gilt.

`log_level`

Logging-Stufe. Sinnvolle Werte sind `DEBUG`, `INFO`, `WARNING` und `ERROR`.

Fuer die Einrichtung ist `DEBUG` hilfreich. Im Dauerbetrieb ist `INFO` meist ausreichend.

`state_file`

Datei fuer persistenten Bridge-Status. Relative Pfade werden relativ zur `config.yaml` aufgeloest. Der Status enthaelt unter anderem die aktive OCPP-Transaktion und den letzten Zaehlerwert.

`log_file`

Optionale Logdatei. Leer lassen, wenn nur auf die Konsole geloggt werden soll:

```yaml
log_file: ""
```

## go-e Messwerte

Bei API v1 werden die Einheiten wie folgt behandelt:

- `eto`: Gesamtzaehler in `0.1 kWh`, wird zu Wh umgerechnet und als OCPP Register verwendet.
- `dws`: Session-Energie in Dezawattsekunden, wird mit `dws / 360` zu Wh umgerechnet.
- `nrg[11]`: Gesamtleistung in `0.01 kW`, wird mit `* 10` zu W umgerechnet.
- `nrg[4..6]`: Strom je Phase in `0.1 A`, wird mit `/ 10` zu A umgerechnet.

Waehrend einer aktiven OCPP-Transaktion sendet die Bridge als `Energy.Active.Import.Register`:

```text
meterStart aus eto + (aktuelles dws - dws beim Transaktionsstart)
```

Damit steigt der OCPP-Zaehler waehrend der Ladung live mit, obwohl `eto` bei alten go-eChargern nur grob in 0,1-kWh-Schritten aktualisiert wird.

## Sichere Erstinbetriebnahme

1. `dry_run: true`
2. `read_only: true`
3. Bridge starten und pruefen, ob BootNotification, Heartbeat, StatusNotification und MeterValues im Backend ankommen.
4. Wenn Telemetrie passt, `read_only: false` setzen.
5. Fuer echte Remote-Steuerung `dry_run: false` und gezielt `allow_remote_start` oder `allow_remote_stop` freigeben.
