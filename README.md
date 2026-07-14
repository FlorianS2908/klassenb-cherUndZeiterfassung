# Klassenbuch Timebutler Tool

Lokales Windows-Tool fuer Klassenbuch-Automation und Zeiterfassung. Das Backend laeuft mit Python 3.11+, FastAPI und Playwright. Die Oberflaeche ist mit React, Vite und TypeScript gebaut.

Der Standardmodus ist immer Dry-Run. Finale Aktionen wie Speichern, Signieren oder Absenden sind nur moeglich, wenn `AUTO_SUBMIT=true` gesetzt ist und die finale Review-Seite bestaetigt wurde.

## Installation Unter Windows

1. Python 3.11 oder neuer installieren.
2. Node.js inklusive npm installieren.
3. Im Projektordner ausfuehren:

```bat
install.bat
```

Das Skript erstellt `.venv`, installiert Backend-Abhaengigkeiten, installiert Playwright-Browser und installiert Frontend-Abhaengigkeiten. Zugangsdaten werden nicht in der Konsole abgefragt.

## Setup

Das Setup laeuft in der Weboberflaeche. Beim ersten Start ohne `.env` oeffnet `start_tool.bat` automatisch [http://localhost:5173/setup](http://localhost:5173/setup). Alternativ kann `setup_env.bat` genutzt werden; die Datei startet ebenfalls das Web-Setup.

Die Weboberflaeche erzeugt lokal eine `.env`. Passwoerter und API-Keys werden nicht im Frontend angezeigt, nicht geloggt und nicht von der Setup-API zurueckgegeben.

Wenn `TIMEBUTLER_USERNAME` oder `TIMEBUTLER_PASSWORD` leer sind, nutzt das Backend automatisch die Klassenbuch-Zugangsdaten.

`setup_env.py` startet keine Konsolenabfragen mehr. Das Skript gibt nur noch den Hinweis auf das Web-Setup unter [http://localhost:5173/setup](http://localhost:5173/setup) aus.

## Start

```bat
start_tool.bat
```

Backend: [http://localhost:8000](http://localhost:8000)  
Frontend: [http://localhost:5173](http://localhost:5173)

Dry-Run bewusst starten:

```bat
dry_run.bat
```

Abhaengigkeiten aktualisieren:

```bat
update_dependencies.bat
```

## Entwicklungsstart

Backend:

```bat
cd backend
python -m app.main
```

Frontend:

```bat
cd frontend
npm install
npm run dev
```

## Bedienung

Dashboard zeigt `RUN_ID`, Modus, `AUTO_SUBMIT`, Zieltag, Sperrtag-Hinweise, Fortschritt und Schrittstatus.

Klassenbuch:

- Datei per Drag-and-Drop hochladen.
- PDF, PPTX, PPT, HTML, Markdown oder TXT verwenden.
- Auswertungsbereich festlegen.
- Beispiele: `1-5`, `1-5, 8, 10-12`, leer = gesamte Datei.
- Vorschau pruefen.
- Analyse startet nur auf dem ausgewaehlten Bereich.
- Die erzeugten 9 UE im Korrekturmodus pruefen.

Zeiterfassung:

- Zieltag, Projekt, Kategorie, Start, Ende, Pause und Bemerkung pruefen.
- Standardwerte kommen aus `.env`.
- Projekt ist standardmaessig `FbW`.
- Kategorie ist standardmaessig `Training/Coaching`.

Review:

- Finale Aktionen sind ohne Review-Bestaetigung gesperrt.
- Bei `AUTO_SUBMIT=false` bleiben finale Buttons deaktiviert.
- Bei `AUTO_SUBMIT=true` muessen alle Validierungen erfolgreich sein.
- Klassenbuch-Signaturen brauchen zusaetzlich die Signatur-Bestaetigung in der Review-Seite.
- Bei TAN, 2FA, Zertifikat, Smartcard oder externer Signaturabfrage bricht das Tool ab und verlangt manuelle Signatur.

## Zieltag Und Sperrtage

Das Tool arbeitet fuer den vorherigen Arbeitstag:

- Montag -> vorheriger Freitag
- Dienstag bis Freitag -> Vortag
- Samstag und Sonntag -> kein automatischer Lauf

Feiertage, `BLOCKED_DATES`, `VACATION_DATES` und `SICK_DATES` verhindern automatische Eintraege. Standard-Bundesland ist `BW`.

## Referenzabbildungen

Referenzscreenshots werden nur zur Entwicklung und Selektor-Strategie verwendet:

```text
C:\Users\Florian.Schaffer\OneDrive - Amadeus Fire AG\Desktop\Private\Klassenbuecher
```

Die Automation nutzt Playwright-Selektoren mit Fallbacks, keine Koordinatenklicks.

## Windows Aufgabenplanung

1. Aufgabenplanung oeffnen.
2. Neue Aufgabe erstellen.
3. Trigger: woechentlich, Montag bis Freitag, 08:20 Uhr.
4. Aktion: Programm starten.
5. Programm: Pfad zu `start_tool.bat` oder `dry_run.bat`.
6. Starten in: Projektordner `klassenbuch-tool`.

Alternative: APScheduler ist im Backend vorbereitet und registriert einen Werktagsjob fuer 08:20 Uhr Europe/Berlin.

## Produktivmodus

Produktivmodus ist absichtlich zweistufig:

1. In `.env` `AUTO_SUBMIT=true` setzen.
2. In der UI die finale Review und die Signatur-Bestaetigung setzen.

Ohne beide Gates wird nichts gespeichert, signiert oder abgesendet.

## Logs, Screenshots Und Fehlerbericht

- Logs: `logs/`
- Screenshots: `screenshots/`
- Fehlerberichte: `error_reports/`
- Analysehistorie: `analysis_history/`

Fehlerberichte enthalten Status, Logs und Screenshots, aber keine Passwoerter, API-Keys, Cookies, Tokens oder Sessiondaten.

## Fehlerbehebung

- `.venv` fehlt: `install.bat` ausfuehren.
- `.env` fehlt: `start_tool.bat` ausfuehren und das Setup im Browser abschliessen.
- Frontend startet nicht: Node.js/npm pruefen und `update_dependencies.bat` ausfuehren.
- Backend startet nicht: Python 3.11+ pruefen und Backend-Abhaengigkeiten installieren.
- Ungueltiger Bereich: Syntax wie `1-5, 8, 10-12` verwenden.
- Produktivbutton deaktiviert: `AUTO_SUBMIT`, Review, Sperrtage und Validierungen pruefen.

## Wiederholbare Analyse

Die gleiche Datei kann mehrfach mit verschiedenen Bereichen analysiert werden, zum Beispiel heute Folien `5-10` und morgen Folien `11-18`. Jeder Lauf wird als eigener Eintrag in der Analysehistorie gespeichert und kann dort wieder geoeffnet werden.

## OpenAI KI-Analyse

Die KI-Analyse sendet nicht die komplette Datei an OpenAI. Das Backend extrahiert lokal nur den ausgewaehlten Bereich, kuerzt ihn bei Bedarf auf `OPENAI_MAX_INPUT_CHARS` und sendet nur diesen Textbereich mit Dateiname, Dateityp und Bereichsmetadaten an die Responses API.

Empfohlene Konfiguration:

```text
OPENAI_API_KEY_FILE=C:\Users\Florian.Schaffer\OneDrive - Amadeus Fire AG\Desktop\KlassenbuchTimebutler\api_key_klassenbuch.txt
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_INPUT_CHARS=30000
OPENAI_TIMEOUT_SECONDS=60
OPENAI_RETRY_COUNT=2
OPENAI_TEMPERATURE=0.2
```

Alternativ kann `OPENAI_API_KEY` direkt in der lokalen `.env` gesetzt werden. Die Key-Datei und `api_key*.txt`, `*.key`, `*.secret`, `secrets/` und `credentials/` sind in `.gitignore` gesperrt. Der API-Key wird nie im Frontend angezeigt, nicht geloggt und nicht in Fehlerberichte geschrieben.

Wenn kein Key vorhanden ist, bleibt das Tool nutzbar: Die Klassenbuch-Seite zeigt den OpenAI-Status und der manuelle Korrekturmodus bleibt verfuegbar.

## GitHub Push

Das Projekt enthaelt eine Sicherheitspruefung vor Commits:

```bat
python scripts\check_before_commit.py
```

Commit und Push:

```bat
commit_and_push.bat "Initial build: Klassenbuch und Timebutler Automatisierung"
```

Das Skript initialisiert Git bei Bedarf, setzt `origin` auf `https://github.com/FlorianS2908/klassenb-cherUndZeiterfassung.git`, prueft `.gitignore`, verhindert sensible Dateien im Git-Index und versucht den Push nach `main`. Wenn `main` geschuetzt ist, wird ein Feature-Branch vorbereitet. GitHub-Zugangsdaten oder Tokens werden nicht abgefragt und nicht gespeichert.
