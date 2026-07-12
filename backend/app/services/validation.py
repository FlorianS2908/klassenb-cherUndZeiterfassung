from __future__ import annotations

import re
from datetime import date, datetime

from app.models.schemas import TimebutlerPayload, UeItem
from app.services.holiday_service import blocked_reason

REQUIRED_LEARNING_FORMAT = "Aufgaben-/Uebungsbesprechung"


def validate_ue_items(items: list[UeItem]) -> list[str]:
    errors: list[str] = []
    if len(items) != 9:
        errors.append("Es muessen genau 9 UE vorhanden sein.")
    for item in items:
        if not item.content.strip():
            errors.append(f"UE {item.number}: Lehrinhalt fehlt.")
        if len(item.formats) > 2:
            errors.append(f"UE {item.number}: maximal zwei Lernformate erlaubt.")
        if REQUIRED_LEARNING_FORMAT not in item.formats:
            errors.append(f"UE {item.number}: Pflicht-Lernformat Aufgaben-/Uebungsbesprechung fehlt.")
    return errors


def validate_timebutler_payload(payload: TimebutlerPayload, federal_state: str, blocked_dates: str, vacation_dates: str, sick_dates: str) -> list[str]:
    errors: list[str] = []
    reason = blocked_reason(payload.target_date, federal_state, blocked_dates, vacation_dates, sick_dates)
    if reason:
        errors.append(reason)
    if not payload.project.strip():
        errors.append("Projekt darf nicht leer sein.")
    if not payload.category.strip():
        errors.append("Kategorie darf nicht leer sein.")
    time_re = re.compile(r"^\d{2}:\d{2}$")
    if not time_re.match(payload.start):
        errors.append("Startzeit muss Format hh:mm haben.")
    if not time_re.match(payload.end):
        errors.append("Endzeit muss Format hh:mm haben.")
    if time_re.match(payload.start) and time_re.match(payload.end):
        start = datetime.strptime(payload.start, "%H:%M").time()
        end = datetime.strptime(payload.end, "%H:%M").time()
        if end <= start:
            errors.append("Endzeit muss nach Startzeit liegen.")
    if not payload.pause.strip():
        errors.append("Pause darf nicht leer sein.")
    return errors


def final_action_allowed(auto_submit: bool, review_confirmed: bool, validation_errors: list[str]) -> tuple[bool, str]:
    if not auto_submit:
        return False, "Produktivaktion gesperrt: AUTO_SUBMIT=false."
    if not review_confirmed:
        return False, "Produktivaktion gesperrt: Review nicht bestaetigt."
    if validation_errors:
        return False, "Produktivaktion gesperrt: Validierungsfehler vorhanden."
    return True, "Produktivaktion erlaubt."
