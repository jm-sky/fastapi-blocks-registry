# Problem z nazwą modułu `logs`

## Problem

Moduł `logs` w projekcie znajduje się w katalogu `app/modules/logs/`, jednak nazwa `logs` jest bardzo często używana w plikach `.gitignore` do ignorowania katalogów z plikami logów aplikacji.

## Obecne rozwiązanie

W projekcie testowym w `.gitignore` znajduje się:

```gitignore
# Logs
*.log
logs/
!app/modules/logs
```

Wyjątek `!app/modules/logs` zapobiega ignorowaniu modułu, ale to rozwiązanie:
- Wymaga ręcznej konfiguracji w każdym projekcie
- Może być łatwo przeoczone przez deweloperów
- Nie jest oczywiste dla nowych użytkowników CLI

## Rekomendacja dla projektów CLI

### Dla `fastapi-blocks-registry`:

Rozważyć zmianę nazwy modułu z `logs` na jedną z alternatyw:

1. **`log-management`** ⭐ **REKOMENDOWANE** - bardzo opisowe, jasno określa przeznaczenie
2. **`logging`** - bardziej opisowe, ale może kolidować z Python `logging` module
3. **`audit-logs`** - jeśli moduł jest używany głównie do audytu
4. **`log-module`** - bezpośrednie, ale może być mylące

### Dla `vue-blocks-registry`:

Jeśli moduł frontendowy również nazywa się `logs`, rozważyć tę samą zmianę dla spójności.

## Zalecana nazwa

**Rekomendacja: `log-management`** ⭐

Powody:
- Jasno określa przeznaczenie modułu (zarządzanie logami)
- Nie koliduje z typowymi wzorcami `.gitignore`
- Jest opisowa i zrozumiała
- Nie wymaga wyjątków w `.gitignore`
- Krótka i czytelna nazwa

## Alternatywne rozwiązanie

Jeśli zmiana nazwy nie jest możliwa, CLI powinno:

1. **Automatycznie dodawać wyjątek do `.gitignore`** podczas instalacji modułu:
   ```gitignore
   # Logs
   *.log
   logs/
   !app/modules/logs  # Added by fastapi-registry add logs
   ```

2. **Wyświetlać ostrzeżenie** podczas instalacji modułu:
   ```
   ⚠️  Warning: Module 'logs' may conflict with .gitignore patterns.
   Make sure to add '!app/modules/logs' to your .gitignore file.
   ```

3. **Dokumentować** w README modułu wymaganie dotyczące `.gitignore`

## Data odkrycia

2025-11-06

## Status

⚠️ **Do rozważenia** - wymaga decyzji w projektach źródłowych CLI

## Powiązane pliki

- `backend/app/modules/logs/` - moduł logs
- `.gitignore` - konfiguracja gitignore z wyjątkiem dla modułu

---

## ✅ RESOLVED

**Status**: Naprawione w v0.2.15 - zmieniono nazwę modułu z `logs` na `log-management`

**Zmiany**:
- Zmieniono nazwę katalogu modułu z `logs` na `log-management` w `fastapi_registry/example_project/app/modules/`
- Zaktualizowano `fastapi_registry/registry.json` - zmieniono klucz z `"logs"` na `"log-management"` i path
- Zaktualizowano `fastapi_registry/example_project/app/api/router.py` - zmieniono import z `app.modules.logs` na `app.modules.log_management`
- Zaktualizowano wszystkie importy w plikach modułu (`__init__.py`, `example_usage.py`, `README.md`)
- Usunięto funkcję `update_gitignore_for_logs_module` z `fastapi_registry/core/file_utils.py` (nie jest już potrzebna)
- Usunięto wywołanie funkcji z `fastapi_registry/core/installer.py`
- Zaktualizowano `CLAUDE.md` - zmieniono referencję w dokumentacji struktury projektu

**Korzyści**:
- Moduł nie koliduje już z typowymi wzorcami `.gitignore` (nie wymaga wyjątków)
- Nazwa jest bardziej opisowa i jasno określa przeznaczenie modułu
- Nie wymaga ręcznej konfiguracji `.gitignore` w każdym projekcie

**Data rozwiązania**: 2025-11-07
