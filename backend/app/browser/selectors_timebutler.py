TIMEBUTLER_SELECTORS = {
    "username": ['input[name="username"]', 'input[type="email"]', 'input[placeholder*="E-Mail"]'],
    "password": ['input[name="password"]', 'input[type="password"]', 'input[placeholder*="Passwort"]'],
    "login_button": ['button:has-text("Anmelden")', 'button[type="submit"]', 'input[type="submit"]'],
    "own_data": ['text="Eigene Daten"', 'a:has-text("Eigene Daten")', '[role="link"]:has-text("Eigene Daten")'],
    "work_time": ['text="Arbeitszeit eintragen"', 'a:has-text("Arbeitszeit eintragen")', '[role="link"]:has-text("Arbeitszeit")'],
    "project": ['select[name*="project"]', 'select:near(:text("Projekt"))', 'input[placeholder*="Projekt"]'],
    "category": ['select[name*="category"]', 'select:near(:text("Kategorie"))', 'input[placeholder*="Kategorie"]'],
    "start": ['input[name*="start"]', 'input[placeholder*="Start"]', 'input:near(:text("Start"))'],
    "end": ['input[name*="end"]', 'input[placeholder*="Ende"]', 'input:near(:text("Ende"))'],
    "pause": ['input[name*="pause"]', 'input[placeholder*="Pause"]', 'input:near(:text("Pause"))'],
    "save_button": ['button:has-text("Speichern")', '[role="button"]:has-text("Speichern")', 'input[value="Speichern"]'],
}
