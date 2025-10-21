# 🧩 FastAPI Blocks Registry — modularny system scaffoldingu backendu

## 🎯 Cel projektu
System podobny do **shadcn-vue**, ale dla backendu w Pythonie (FastAPI).  
Pozwala dodawać do projektu gotowe **moduły** (np. `auth`, `users`, `billing`, `projects`) jedną komendą CLI, kopiując kompletne komponenty — modele, schematy, routery, serwisy, konfiguracje i zależności.

---

## 🚀 Założenia

- Moduły backendowe są przechowywane w **registry** (lokalnym lub zdalnym, np. PyPI, GitHub Registry).
- Użytkownik może zainstalować i dodać moduł do projektu komendą:
  ```bash
  fastapi-registry add auth
  ```
- Każdy moduł zawiera gotowe pliki, które są kopiowane do projektu (`app/modules/auth/`).
- System automatycznie:
  - aktualizuje `main.py` (dodaje router),
  - aktualizuje `requirements.txt` (dodaje zależności modułu),
  - może dodać wpisy do `.env` (np. JWT_SECRET),
  - kopiuje gotowe configi / dependency injection.

---

## 📁 Struktura katalogu paczki `fastapi_registry`

```
fastapi_registry/
  ├─ __init__.py
  ├─ cli.py
  ├─ registry.json
  ├─ modules/
  │   ├─ auth/
  │   │   ├─ models.py
  │   │   ├─ schemas.py
  │   │   ├─ router.py
  │   │   ├─ service.py
  │   │   ├─ dependencies.py
  │   │   ├─ __init__.py
  │   │   └─ template_config.json
  │   └─ users/
  │       └─ ...
  └─ templates/
      └─ ... (jeśli niektóre pliki generowane dynamicznie)
```

---

## ⚙️ Plik `registry.json` (meta-informacje o modułach)

```json
{
  "auth": {
    "name": "Authentication",
    "description": "JWT-based authentication with refresh tokens and user management",
    "path": "modules/auth",
    "dependencies": [
      "python-jose[cryptography]",
      "passlib[bcrypt]",
      "bcrypt"
    ],
    "env": {
      "JWT_SECRET_KEY": "change-me",
      "JWT_EXPIRE_MINUTES": "60"
    }
  },
  "users": {
    "name": "User Management",
    "description": "CRUD endpoints for user management",
    "path": "modules/users",
    "dependencies": []
  }
}
```

---

## 🧠 Komponenty modułu (np. `auth`)

- `models.py` — modele SQLAlchemy (`User`, `RefreshToken`, itp.)
- `schemas.py` — schematy Pydantic (`UserCreate`, `Token`, itp.)
- `router.py` — definicje endpointów FastAPI
- `service.py` — logika domenowa (np. weryfikacja hasła, generowanie tokenów)
- `dependencies.py` — zależności dla FastAPI (np. `get_current_user`)
- `__init__.py` — inicjalizacja modułu, np. `router = APIRouter(...)`

---

## 🧰 CLI — główne komendy

### `fastapi-registry list`
Wyświetla dostępne moduły z registry.json  
(przykład analogiczny do `npx shadcn@latest list`)

### `fastapi-registry add <module>`
Dodaje moduł do projektu:
- kopiuje pliki do `/app/modules/<module>/`
- dopisuje `include_router(...)` do `main.py`
- dopisuje zależności do `requirements.txt`
- ustawia zmienne ENV

### `fastapi-registry remove <module>`
Usuwa moduł i aktualizuje konfigurację projektu.

---

## 🧩 CLI — implementacja (Typer)

- Framework CLI: [**Typer**](https://typer.tiangolo.com/)
- Operacje plikowe: `shutil`, `os`, `pathlib`
- Parsowanie JSON: `json` standardowy
- Szablony dynamiczne: opcjonalnie `cookiecutter`

---

## 🪄 Przykład użycia w projekcie

```bash
pip install fastapi-registry
fastapi-registry add auth
```

Automatycznie:
1. Kopiuje katalog `auth` do `app/modules/auth/`
2. Dopisuje do `main.py`:
   ```python
   from app.modules.auth.router import router as auth_router
   app.include_router(auth_router, prefix="/auth", tags=["Auth"])
   ```
3. Dodaje zależności do `requirements.txt`
4. Dodaje brakujące wpisy do `.env`

---

## 🔧 Przykład kodu CLI (`cli.py`)

```python
import typer, json, shutil
from pathlib import Path

app = typer.Typer()

@app.command()
def list():
    with open("registry.json") as f:
        registry = json.load(f)
    for name, data in registry.items():
        typer.echo(f"- {name}: {data['description']}")

@app.command()
def add(module: str):
    base = Path(__file__).parent
    with open(base / "registry.json") as f:
        registry = json.load(f)
    if module not in registry:
        typer.echo(f"Module '{module}' not found.")
        raise typer.Exit(1)

    src = base / registry[module]["path"]
    dst = Path.cwd() / "app" / "modules" / module
    shutil.copytree(src, dst, dirs_exist_ok=True)
    typer.echo(f"✅ Added module '{module}'")

if __name__ == "__main__":
    app()
```

---

## 🔮 Możliwe rozszerzenia

- Wsparcie dla **customowych registry URL** (np. GitHub repo)
- Integracja z **PyPI** (`pip install fastapi-registry[auth]`)
- Generator testów (`pytest`) dla każdego modułu
- System hooków (`on_add`, `on_remove`)
- Integracja z Docker Compose (np. dodanie Redis, PostgreSQL)
- Możliwość scaffoldingu całych domen (`billing`, `crm`, `projects`)

---

## 🧠 Inspiracje

- [shadcn-vue](https://github.com/shadcn-ui/ui)
- [cookiecutter](https://cookiecutter.readthedocs.io/)
- [Typer (by Sebastián Ramírez)](https://typer.tiangolo.com/)
- [FastAPI Project Generators](https://fastapi.tiangolo.com/project-generation/)

---

## 🏷️ Propozycje nazw

- `fastapi-registry` *(czytelne i opisowe)*
- `fastcn` *(luźne nawiązanie do shadcn)*
- `fuseapi` *(od „fuse” – łączenie modułów)*
- `fastapi-fuse`
- `fastapi-modules`

---

## 🧭 Kierunek rozwoju

1. Prototyp CLI + 1 moduł `auth`
2. System registry + CLI komendy (`list`, `add`, `remove`)
3. Publikacja na PyPI
4. Integracja z GitHub Registry (zdalne moduły)
5. Dodanie nowych modułów (`users`, `projects`, `billing`, `emails`)
6. Integracja z CI (np. GitHub Actions do automatycznego budowania registry)

---
