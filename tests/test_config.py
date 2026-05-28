from core.config import Settings

def test_settings_structure():
    """Validates that the Settings class has the required attributes correctly loaded."""
    settings = Settings()
    
    # 1. Validamos que los atributos existan en la clase
    assert hasattr(settings, "TELEGRAM_TOKEN")
    assert hasattr(settings, "GEMINI_API_KEY")
    assert hasattr(settings, "SHEETS_CREDENTIALS")
    
    # 2. Validamos que no estén vacíos (None o strings vacíos)
    # Al usar bool(), si la variable tiene texto devolverá True, si es None o "" devolverá False.
    # Así verificamos que cargaron bien sin comparar directamente su valor secreto.
    assert bool(settings.TELEGRAM_TOKEN) is True
    assert bool(settings.GEMINI_API_KEY) is True
    assert bool(settings.SHEETS_CREDENTIALS) is True