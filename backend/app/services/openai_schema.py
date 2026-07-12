from __future__ import annotations

ALLOWED_FORMATS = [
    "Frontalunterricht/Vortrag",
    "Gruppenarbeit",
    "betreute Einzelarbeit",
    "Projektarbeit",
    "Aufgaben-/Übungsbesprechung",
    "Fallstudie",
    "Rollenspiel",
    "Lehr-/Lerngespräch",
    "Präsentation/Demonstration",
    "Lernerfolgskontrolle/Prüfung",
    "Projektaufgabe",
    "n/a",
]

OPENAI_UE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["file_name", "selected_range", "selected_item_count", "source_summary", "confidence_score", "detected_topics", "unterrichtseinheiten", "warnings"],
    "properties": {
        "file_name": {"type": "string"},
        "selected_range": {"type": "string"},
        "selected_item_count": {"type": "integer", "minimum": 1},
        "source_summary": {"type": "string"},
        "confidence_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "detected_topics": {"type": "array", "items": {"type": "string"}},
        "unterrichtseinheiten": {
            "type": "array",
            "minItems": 9,
            "maxItems": 9,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["ue", "lehrinhalt", "lernformate"],
                "properties": {
                    "ue": {"type": "integer", "minimum": 1, "maximum": 9},
                    "lehrinhalt": {"type": "string", "minLength": 40, "maxLength": 220},
                    "lernformate": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 2,
                        "items": {"type": "string", "enum": ALLOWED_FORMATS},
                    },
                },
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}
