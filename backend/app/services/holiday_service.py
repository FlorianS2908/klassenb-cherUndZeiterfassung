from __future__ import annotations

from datetime import date

import holidays

from app.services.date_service import parse_date_list


def is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def is_holiday(day: date, federal_state: str = "BW") -> bool:
    return day in holidays.country_holidays("DE", subdiv=federal_state.upper())


def blocked_reason(day: date, federal_state: str, blocked_dates: str, vacation_dates: str, sick_dates: str) -> str:
    if is_weekend(day):
        return "Zieltag ist Samstag oder Sonntag"
    if is_holiday(day, federal_state):
        return "Zieltag ist gesetzlicher Feiertag"
    if day in parse_date_list(blocked_dates):
        return "Zieltag ist gesperrt"
    if day in parse_date_list(vacation_dates):
        return "Zieltag ist Urlaubstag"
    if day in parse_date_list(sick_dates):
        return "Zieltag ist Krankheitstag"
    return ""
