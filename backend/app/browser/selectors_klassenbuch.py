KLASSENBUCH_SELECTORS = {
    "username": ['input[name="username"]', 'input[type="email"]', 'input[placeholder*="Benutzer"]', 'input[placeholder*="E-Mail"]'],
    "password": ['input[name="password"]', 'input[type="password"]', 'input[placeholder*="Passwort"]'],
    "login_button": ['button:has-text("Anmelden")', 'button[type="submit"]', 'input[type="submit"]'],
    "overview_markers": ['text="Themendokumentationen"', 'text="Offen"', 'table'],
    "edit_button": ['button:has-text("Bearbeiten")', 'a:has-text("Bearbeiten")', '[title*="Bearbeiten"]', '[aria-label*="Bearbeiten"]', 'a:has-text("Edit")'],
    "ue_tab": ['text="Unterrichtseinheiten"', 'button:has-text("Unterrichtseinheiten")', 'a:has-text("Unterrichtseinheiten")', 'text="UE"'],
    "content_fields": ['textarea', 'input[type="text"]', '[contenteditable="true"]'],
    "save_button": ['button:has-text("Speichern")', '[role="button"]:has-text("Speichern")', 'input[value="Speichern"]'],
    "next_button": ['button:has-text("Weiter")', '[role="button"]:has-text("Weiter")', 'a:has-text("Weiter")'],
    "signature": ['input[name*="sign"]', 'input[placeholder*="Sign"]', 'textarea[name*="sign"]', 'input:near(:text("Signatur"))'],
    "sign_button": ['button:has-text("Signieren")', 'button:has-text("Abschliessen")', 'button:has-text("Abschließen")'],
}
