from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models.schemas import UeItem
from app.services.openai_schema import OPENAI_UE_SCHEMA
from app.services.ue_planner import plan_nine_ue

REQUIRED_FORMAT = "Aufgaben-/Uebungsbesprechung"
DEFAULT_SECOND_FORMAT = "betreute Einzelarbeit"


@dataclass(frozen=True)
class OpenAIKeyStatus:
    active: bool
    key_present: bool
    source: str
    message: str
    display_path: str = ""


@dataclass(frozen=True)
class OpenAIAnalysis:
    used_ai: bool
    topics: list[str]
    confidence_score: float
    ue_items: list[UeItem]
    warnings: list[str]
    source_summary: str = ""
    truncated: bool = False
    error: str = ""


def _short_path(path: str) -> str:
    if not path:
        return ""
    parts = Path(path).parts
    if len(parts) <= 3:
        return path
    return "..." + "\\" + "\\".join(parts[-3:])


def load_api_key() -> tuple[str, OpenAIKeyStatus]:
    settings = get_settings()
    key_file = settings.openai_api_key_file.strip()
    if key_file:
        path = Path(key_file)
        if not path.exists():
            return "", OpenAIKeyStatus(False, False, "missing_file", "OpenAI API-Key-Datei wurde nicht gefunden. KI-Analyse ist deaktiviert.", _short_path(key_file))
        try:
            key = path.read_text(encoding="utf-8", errors="ignore").strip().replace("\n", "").replace("\r", "")
        except OSError:
            return "", OpenAIKeyStatus(False, False, "missing_file", "OpenAI API-Key-Datei ist nicht lesbar.", _short_path(key_file))
        if not key:
            return "", OpenAIKeyStatus(False, False, "empty_file", "OpenAI API-Key-Datei ist leer.", _short_path(key_file))
        return key, OpenAIKeyStatus(True, True, "file", "OpenAI API ist aktiv.", _short_path(key_file))
    key = settings.openai_api_key.strip()
    if key:
        return key, OpenAIKeyStatus(True, True, "env", "OpenAI API ist aktiv.")
    return "", OpenAIKeyStatus(False, False, "none", "Kein OpenAI API-Key hinterlegt. KI-Analyse ist deaktiviert.")


def public_status() -> dict[str, Any]:
    settings = get_settings()
    _, status = load_api_key()
    return {
        "active": status.active,
        "key_present": status.key_present,
        "source": status.source,
        "message": status.message,
        "display_path": status.display_path,
        "model": settings.openai_model or "gpt-4o-mini",
        "max_input_chars": settings.openai_max_input_chars,
    }


def trim_text(text: str) -> tuple[str, bool]:
    max_chars = max(1000, get_settings().openai_max_input_chars)
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def normalize_format(value: str) -> str:
    mapping = {
        "Aufgaben-/Übungsbesprechung": REQUIRED_FORMAT,
        "Lehr-/Lerngespräch": "Lehr-/Lerngespraech",
        "Präsentation/Demonstration": "Praesentation/Demonstration",
        "Lernerfolgskontrolle/Prüfung": "Lernerfolgskontrolle/Pruefung",
    }
    return mapping.get(value, value)


def normalize_ue_items(raw_items: list[dict[str, Any]]) -> list[UeItem]:
    if len(raw_items) != 9:
        raise ValueError("KI-Antwort enthaelt nicht genau 9 UE.")
    normalized: list[UeItem] = []
    seen_numbers = set()
    for raw in raw_items:
        number = int(raw.get("ue", 0))
        if number < 1 or number > 9 or number in seen_numbers:
            raise ValueError("KI-Antwort enthaelt ungueltige UE-Nummern.")
        seen_numbers.add(number)
        content = str(raw.get("lehrinhalt", "")).strip()
        if not 40 <= len(content) <= 220:
            raise ValueError("KI-Antwort enthaelt Lehrinhalte ausserhalb der erlaubten Laenge.")
        formats = [normalize_format(str(item)) for item in raw.get("lernformate", [])]
        if REQUIRED_FORMAT not in formats:
            formats.append(REQUIRED_FORMAT)
        if len(formats) > 2:
            formats = [DEFAULT_SECOND_FORMAT, REQUIRED_FORMAT]
        if DEFAULT_SECOND_FORMAT in formats and REQUIRED_FORMAT in formats:
            formats = [REQUIRED_FORMAT, DEFAULT_SECOND_FORMAT]
        normalized.append(UeItem(number=number, content=content, formats=formats[:2]))
    return sorted(normalized, key=lambda item: item.number)


def parse_structured_response(payload: dict[str, Any]) -> OpenAIAnalysis:
    items = normalize_ue_items(payload.get("unterrichtseinheiten", []))
    confidence = int(payload.get("confidence_score", 0)) / 100
    warnings = [str(item) for item in payload.get("warnings", [])]
    if confidence < 0.5:
        warnings.append("confidence_score unter 50: automatische Eintragung gesperrt.")
    return OpenAIAnalysis(
        used_ai=True,
        topics=[str(item) for item in payload.get("detected_topics", [])],
        confidence_score=confidence,
        ue_items=items,
        warnings=warnings,
        source_summary=str(payload.get("source_summary", "")),
    )


def build_prompts(file_name: str, file_type: str, total_items_label: str, selected_range: str, selected_item_count: int, extracted_text: str) -> tuple[str, str]:
    system_prompt = (
        "Du bist ein sachlicher Assistent fuer Klassenbuch-Dokumentation in der beruflichen IT-Ausbildung. "
        "Du erstellst aus Unterrichtsmaterialien genau 9 kurze Unterrichtseinheiten. Formuliere neutral, knapp und dokumentativ. "
        "Nutze nur die Inhalte aus dem uebergebenen ausgewaehlten Bereich. Erfinde keine Themen aus nicht uebergebenen Folien, Seiten oder Abschnitten. "
        "Jede UE muss fuer ein offizielles Klassenbuch geeignet sein. Keine Markdown-Syntax. Keine HTML-Tags. Keine Aufzaehlungszeichen in den Lehrinhalten. "
        "Jede UE muss das Lernformat Aufgaben-/Übungsbesprechung enthalten. Standardmaessig soll zusaetzlich betreute Einzelarbeit verwendet werden. "
        "Gib ausschliesslich valides JSON gemaess Schema zurueck."
    )
    user_prompt = f"""Datei:
{file_name}

Dateityp:
{file_type}

Gesamtumfang:
{total_items_label}

Ausgewaehlter Bereich:
{selected_range or "gesamte Datei"}

Anzahl ausgewaehlter Elemente:
{selected_item_count}

Extrahierter Text aus dem ausgewaehlten Bereich:
{extracted_text}

Aufgabe:
Erstelle daraus genau 9 Unterrichtseinheiten fuer das Klassenbuch.
Jede Unterrichtseinheit soll einen kurzen Lehrinhalt enthalten.
Jede Unterrichtseinheit muss das Lernformat Aufgaben-/Übungsbesprechung enthalten.
Standardmaessig zusaetzlich betreute Einzelarbeit verwenden.
Gib einen confidence_score von 0 bis 100 an.
Wenn der ausgewaehlte Bereich wenig Inhalt enthaelt, setze den confidence_score entsprechend niedriger und ergaenze warnings."""
    return system_prompt, user_prompt


async def analyze_with_openai(file_name: str, file_type: str, total_items_label: str, selected_range: str, selected_item_count: int, extracted_text: str) -> OpenAIAnalysis:
    settings = get_settings()
    key, status = load_api_key()
    trimmed_text, truncated = trim_text(extracted_text)
    if not status.active or not key:
        topics, confidence, items = plan_nine_ue(trimmed_text)
        return OpenAIAnalysis(False, topics, confidence, items, [status.message], truncated=truncated, error=status.message)
    system_prompt, user_prompt = build_prompts(file_name, file_type, total_items_label, selected_range, selected_item_count, trimmed_text)
    last_error = ""
    for attempt in range(settings.openai_retry_count + 1):
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=key, timeout=settings.openai_timeout_seconds)
            response = await client.responses.create(
                model=settings.openai_model or "gpt-4o-mini",
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "klassenbuch_ue_analysis",
                        "schema": OPENAI_UE_SCHEMA,
                        "strict": True,
                    }
                },
                temperature=settings.openai_temperature,
                store=False,
            )
            raw_text = getattr(response, "output_text", "")
            if not raw_text:
                raw_text = response.output[0].content[0].text
            result = parse_structured_response(json.loads(raw_text))
            logging.info("KI-Analyse erfolgreich: model=%s source=%s range=%s chars=%s confidence=%s warnings=%s", settings.openai_model, status.source, selected_range, len(trimmed_text), result.confidence_score, len(result.warnings))
            return OpenAIAnalysis(True, result.topics, result.confidence_score, result.ue_items, result.warnings, result.source_summary, truncated)
        except Exception as exc:
            last_error = exc.__class__.__name__
            logging.warning("KI-Analyse fehlgeschlagen: model=%s source=%s attempt=%s error=%s", settings.openai_model, status.source, attempt + 1, last_error)
            if attempt < settings.openai_retry_count:
                await asyncio.sleep(1)
    topics, confidence, items = plan_nine_ue(trimmed_text)
    return OpenAIAnalysis(False, topics, confidence, items, [f"KI-Analyse fehlgeschlagen: {last_error}"], truncated=truncated, error=last_error)


async def analyze_topics(text: str) -> tuple[list[str], float, list[UeItem]]:
    result = await analyze_with_openai("", "Text", "Text", "", 1, text)
    return result.topics, result.confidence_score, result.ue_items
