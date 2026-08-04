# opencloud-ocrmyscan

Diese Stack ist so angepasst, dass die komplette Konfiguration über die Environment-Datei gesteuert wird.

## Wichtige Punkte

- Die Konfiguration liegt zentral in der .env-Datei.
- Pfade, OCR-Optionen, Watcher-Intervall und die Scan-zu-WebDAV-Zuordnungen sind über Umgebungsvariablen konfigurierbar.
- Der Ordner ist für ein späteres Git-Repository vorbereitet.

## Beispiel

Die Datei .env enthält bereits die Standardwerte für den aktuellen Einsatz.

## Start

```bash
docker compose up -d --build
```
