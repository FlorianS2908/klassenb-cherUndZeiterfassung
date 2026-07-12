KLASSENBUCH_SELECTORS = {
    "username": ['input[name="username"]', 'input[type="email"]', 'input[placeholder*="Benutzer"]'],
    "password": ['input[name="password"]', 'input[type="password"]', 'input[placeholder*="Passwort"]'],
    "login_button": ['button:has-text("Anmelden")', 'button[type="submit"]', 'input[type="submit"]'],
    "save_button": ['button:has-text("Speichern")', '[role="button"]:has-text("Speichern")', 'input[value="Speichern"]'],
    "next_button": ['button:has-text("Weiter")', '[role="button"]:has-text("Weiter")', 'a:has-text("Weiter")'],
    "signature": ['input[name*="sign"]', 'input[placeholder*="Sign"]', 'textarea[name*="sign"]'],
    "sign_button": ['button:has-text("Signieren")', 'button:has-text("Abschließen")', 'button:has-text("Abschliessen")'],
}
