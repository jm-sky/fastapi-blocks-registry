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

## Data rozwiązania

2025-11-06

## Status

✅ **Rozwiązane** - automatyczne dodawanie wyjątku do .gitignore

### Zrealizowane:
- ✅ Funkcja `update_gitignore_for_logs_module()` w `file_utils.py`
- ✅ Automatyczne dodawanie wyjątku `!app/modules/logs` podczas instalacji modułu logs
- ✅ Integracja z `ModuleInstaller.install_module()`
- ✅ Sprawdzanie, czy wyjątek już istnieje (zapobiega duplikatom)
- ✅ Dodawanie komentarza "# Added by fastapi-registry for logs module"

### Rozwiązanie:
Zamiast zmieniać nazwę modułu (co byłoby breaking change), CLI automatycznie dodaje wyjątek do `.gitignore` podczas instalacji modułu `logs`. To rozwiązanie:
- ✅ Nie wymaga zmian w istniejących projektach
- ✅ Działa automatycznie dla nowych instalacji
- ✅ Jest przejrzyste (komentarz wyjaśnia pochodzenie)
- ✅ Nie wymaga ręcznej konfiguracji przez deweloperów

## Powiązane pliki

- `backend/app/modules/logs/` - moduł logs
- `.gitignore` - konfiguracja gitignore z wyjątkiem dla modułu

