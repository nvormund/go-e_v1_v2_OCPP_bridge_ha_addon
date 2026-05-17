# go-e v1_v2 OCPP Bridge

Diese App verbindet einen go-eCharger ueber die lokale HTTP API mit einem externen OCPP-1.6-Backend.

Sie veraendert Home Assistant nicht. Die App laeuft als eigener Container, liest keine Home-Assistant-Tokens und ruft keine Home-Assistant-API auf.

## Erste Einrichtung

1. Trage unter **go-e Wallbox** die lokale IP-Adresse der Wallbox ein.
2. Lasse **go-e API-Version** zuerst auf `auto`.
3. Trage unter **OCPP-Backend** die WebSocket-URL und Charge-Point-ID aus deinem Backend ein.
4. Starte mit diesen sicheren Einstellungen:

```yaml
dry_run: true
read_only: true
allow_remote_start: false
allow_remote_stop: true
```

5. Starte die App und pruefe im Backend, ob die Wallbox online ist und Messwerte ankommen.
6. Wenn Status und Messwerte passen, setze `read_only` auf `false`.
7. Fuer echte Steuerung setze `dry_run` auf `false`.
8. Fuer Start per Backend setze zusaetzlich `allow_remote_start` auf `true`.

## Was die Sicherheitsfelder bedeuten

`dry_run`

Wenn aktiv, sendet die App keine Start- oder Stop-Kommandos an die Wallbox.

`read_only`

Wenn aktiv, werden RemoteStart und RemoteStop blockiert. Status und Messwerte werden trotzdem gesendet.

`allow_remote_start`

Erlaubt RemoteStartTransaction vom Backend. Das wirkt nur, wenn `dry_run` und `read_only` ausgeschaltet sind.

`allow_remote_stop`

Erlaubt RemoteStopTransaction vom Backend. Das wirkt nur, wenn `dry_run` und `read_only` ausgeschaltet sind.

## Messwerte

Bei go-e API v1 werden die Einheiten der Wallbox umgerechnet:

- `eto`: Gesamtzaehler in `0.1 kWh`
- `dws`: Session-Energie in Dezawattsekunden
- `nrg[11]`: Gesamtleistung in `0.01 kW`
- `nrg[4..6]`: Strom je Phase in `0.1 A`

OCPP bekommt `Energy.Active.Import.Register` in Wh, `Power.Active.Import` in W, `Current.Import` in A und `Voltage` in V.

## Fehlerbehebung

Wenn die App im Backend offline wirkt:

- Pruefe, ob die `backend_url` exakt stimmt.
- Pruefe, ob die `charge_point_id` im Backend angelegt ist.
- Pruefe das App-Log in Home Assistant.
- Lasse `log_level` waehrend der Einrichtung auf `DEBUG`.

Wenn die Wallbox nicht gesteuert wird:

- `dry_run` muss `false` sein.
- `read_only` muss `false` sein.
- Fuer Start muss `allow_remote_start` `true` sein.
- Fuer Stop muss `allow_remote_stop` `true` sein.
