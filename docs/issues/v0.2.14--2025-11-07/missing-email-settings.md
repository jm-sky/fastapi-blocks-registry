# Brakująca konfiguracja EmailSettings w app/core/config.py

## Problem

Nowy moduł email wymaga `EmailSettings` w konfiguracji, ale klasa nie jest zdefiniowana w `app/core/config.py`.

### Błąd

```
ImportError: cannot import name 'EmailSettings' from 'app.core.config'
```

### Lokalizacja błędu

Plik: `backend/app/core/email/service.py` (linia 9)
```python
from app.core.config import EmailSettings, settings
```

### Przyczyna

CLI `fastapi-blocks-registry` dodał moduł email z zależnością od `EmailSettings`, ale nie zaktualizował pliku konfiguracji.

## Wersje CLI, w których występuje problem

- ✅ **v0.2.13** - problem występuje

## Priorytet

🔴 **KRYTYCZNY** - Uniemożliwia uruchomienie aplikacji

## Rekomendacja

1. CLI powinno automatycznie dodawać wymagane klasy konfiguracyjne podczas instalacji modułu email
2. Sprawdzić czy wszystkie zależności modułów są poprawnie zdefiniowane
3. Dodać walidację zależności podczas generowania kodu

## Workaround

Dodać `EmailSettings` do `app/core/config.py` ręcznie lub zainstalować moduł email ponownie po aktualizacji CLI.

---

## ✅ RESOLVED

**Status**: Naprawione w v0.2.14

**Zmiany**:
- Dodano funkcję `add_email_settings_to_config` w `fastapi_registry/core/file_utils.py`:
  - Automatycznie dodaje klasę `EmailSettings` do `config.py`
  - Dodaje pole `email: EmailSettings` do klasy `Settings`
  - Sprawdza i dodaje import `Literal` z `typing` jeśli brakuje
  - Idempotentna - nie dodaje duplikatów
- Dodano pole `config_dependencies` do `ModuleMetadata` w `fastapi_registry/core/registry_manager.py`
- Zaktualizowano `fastapi_registry/registry.json`:
  - Dodano `"config_dependencies": ["email"]` do modułu `auth`
  - Dodano `"config_dependencies": ["email"]` do modułu `two_factor`
- Zintegrowano z `fastapi_registry/core/installer.py`:
  - Przy instalacji modułu sprawdzane są `config_dependencies`
  - Jeśli moduł wymaga `email`, automatycznie dodawany jest `EmailSettings` do `config.py`

**Data rozwiązania**: 2025-11-07
