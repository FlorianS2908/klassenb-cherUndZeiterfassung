# Klassenbuch Timebutler Tool

Lokales Windows-Tool fuer Klassenbuch-Automation und Zeiterfassung. Das Backend laeuft mit Python 3.11+, FastAPI und Playwright. Die Oberflaeche ist mit React, Vite und TypeScript gebaut.

Der Standardmodus ist immer Dry-Run. Finale Aktionen wie Speichern, Signieren oder Absenden sind nur moeglich, wenn `AUTO_SUBMIT=true` gesetzt ist und die finale Review-Seite bestaetigt wurde.

## Start Unter Windows

Es gibt nur noch eine nutzerrelevante Startdatei:

```bat
KlassenbuchTool_starten.bat
```

Neuer Ablauf:

1. Repository herunterladen oder klonen.
2. `KlassenbuchTool_starten.bat` doppelklicken.
3. Das Tool prueft Python, `.venv`, Backend-Abhaengigkeiten, Playwright, Node.js/npm und Frontend-Abhaengigkeiten automatisch.
4. Wenn Node.js/npm fehlt, wird portable Node.js lokal unter `.tools/` vorbereitet. Keine Admin-Rechte noetig.
5. Backend und Frontend starten automatisch.
6. Der Browser oeffnet automatisch.
7. Wenn noch keine `.env` vorhanden ist, oeffnet sich [http://localhost:5173/setup](http://localhost:5173/setup).
8. Zugangsdaten werden in der UI eingetragen.
9. Danach Dashboard nutzen.

Bei Fehlern bleibt das Fenster offen. Zugangsdaten, Passwoerter, API-Keys und `.env`-Inhalte werden nicht in der CMD abgefragt oder angezeigt.

## Setup

Das Setup laeuft in der Weboberflaeche. Beim ersten Start ohne `.env` oeffnet `KlassenbuchTool_starten.bat` automatisch [http://localhost:5173/setup](http://localhost:5173/setup).

Die Weboberflaeche erzeugt lokal eine `.env`. Passwoerter und API-Keys werden nicht im Frontend angezeigt, nicht geloggt und nicht von der Setup-API zurueckgegeben.

Wenn `TIMEBUTLER_USERNAME` oder `TIMEBUTLER_PASSWORD` leer sind, nutzt das Backend automatisch die Klassenbuch-Zugangsdaten.

`setup_env.py` startet keine Konsolenabfragen mehr. Das Skript gibt nur noch den Hinweis auf das Web-Setup unter [http://localhost:5173/setup](http://localhost:5173/setup) aus.

Backend: [http://localhost:8000](http://localhost:8000)  
Frontend: [http://localhost:5173](http://localhost:5173)

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
5. Programm: Pfad zu `KlassenbuchTool_starten.bat`.
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

- `.venv` fehlt: `KlassenbuchTool_starten.bat` erneut starten; die Datei erstellt `.venv` automatisch.
- `.env` fehlt: `KlassenbuchTool_starten.bat` ausfuehren und das Setup im Browser abschliessen.
- Frontend startet nicht: `KlassenbuchTool_starten.bat` erneut starten; fehlende Frontend-Abhaengigkeiten werden automatisch installiert.
- Backend startet nicht: Python 3.11+ pruefen und `KlassenbuchTool_starten.bat` erneut starten.
- Ungueltiger Bereich: Syntax wie `1-5, 8, 10-12` verwenden.
- Produktivbutton deaktiviert: `AUTO_SUBMIT`, Review, Sperrtage und Validierungen pruefen.

### Playwright startet auf Windows nicht

Wenn die Diagnose `Playwright-Browserstart fehlgeschlagen` oder `NotImplementedError` meldet:

1. Tool schliessen.
2. `KlassenbuchTool_starten.bat` neu starten.
3. Sicherstellen, dass das Backend ohne Uvicorn `reload` laeuft.
4. In der aktivierten `.venv` ausfuehren:

```bat
python -m playwright install
```

5. In der UI den Browser-Check ausfuehren.
6. Falls weiterhin Fehler auftreten: `diagnostics/klassenbuch/<RUN_ID>/summary.json` pruefen.

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

## Git Und Sicherheitspruefung

Das Projekt enthaelt eine Sicherheitspruefung vor Commits:

```bat
python scripts\check_before_commit.py
```

Git-Aktionen laufen manuell, ueber Codex oder GitHub Desktop. Die Sicherheitspruefung verhindert sensible Dateien im Git-Index.
