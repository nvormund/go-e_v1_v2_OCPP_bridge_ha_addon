# go-e v1_v2 OCPP Bridge Home Assistant App

Dieses Repository stellt die `go-e v1_v2 OCPP Bridge` als Home Assistant App bereit. Die App laeuft als eigener Container neben Home Assistant und verwendet keine Home-Assistant-API, keine Tokens und keine Home-Assistant-Konfigurationsdateien.

## Installation in Home Assistant OS

1. Home Assistant oeffnen.
2. Zu **Einstellungen > Apps** wechseln.
3. Rechts oben das Menue fuer Repositories oeffnen.
4. Die URL dieses GitHub-Repositories einfuegen und speichern.
5. **go-e v1_v2 OCPP Bridge** installieren.
6. In der App-Konfiguration die Felder ausfuellen.
7. Zuerst mit `dry_run: true` und `read_only: true` starten.

Details zu allen Feldern stehen in der App-Dokumentation.

## Lokaler Test auf Home Assistant OS

Fuer einen schnellen lokalen Test kann der Ordner `goe_ocpp_bridge` in das lokale Add-on/App-Verzeichnis von Home Assistant kopiert werden. Danach im App Store die lokalen Apps neu laden und die App installieren.

Fuer die Weitergabe an andere Nutzer ist ein GitHub-Repository praktischer:

```text
goe-ocpp-bridge-ha-addon/
  repository.yaml
  goe_ocpp_bridge/
    config.yaml
    Dockerfile
    run.sh
    README.md
    DOCS.md
    CHANGELOG.md
    translations/
    bridge/
```

Das Repository muss als GitHub-URL im Home-Assistant-App-Store hinzugefuegt werden. Home Assistant baut die App lokal, weil in `config.yaml` bewusst kein fertiges `image` hinterlegt ist.

## Vor der Veroeffentlichung anpassen

In `repository.yaml` und `goe_ocpp_bridge/config.yaml` ist aktuell eine Platzhalter-URL eingetragen. Vor einer Veroeffentlichung sollte dort die echte GitHub-URL des Repositories stehen.

## Zielgruppe

Diese App ist fuer Nutzer gedacht, die einen go-eCharger ueber dessen lokale HTTP API an ein externes OCPP-1.6-Backend anbinden moechten, ohne Home Assistant selbst zu veraendern.
