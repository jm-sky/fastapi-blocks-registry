# Plan Implementacji - FastAPI Blocks Registry

## Przegląd

Ten dokument opisuje plan implementacji systemu scaffolding dla FastAPI, który będzie generował strukturę katalogów zgodnie z zaproponowanym schematem oraz umożliwiał dodawanie modułów biznesowych.

## 1. Struktura Scaffolding Core

### 1.1 Moduł `core/` - Generowany przez scaffolding

#### `core/config.py`
- **Cel**: Centralna konfiguracja aplikacji
- **Zawartość**:
  - `BaseSettings` z Pydantic
  - Nested configuration classes dla każdego modułu
  - Environment variables validation
  - Database connection settings
  - JWT settings
  - Logging configuration
  - Feature flags

#### `core/factory.py`
- **Cel**: Factory pattern dla tworzenia aplikacji FastAPI
- **Zawartość**:
  - `AppFactory` class
  - `create_app()` function
  - Middleware registration
  - Router registration
  - Exception handlers setup
  - Event handlers (startup/shutdown)

#### `core/middlewares.py`
- **Cel**: Globalne middleware aplikacji
- **Zawartość**:
  - CORS middleware
  - Request logging middleware
  - Rate limiting middleware
  - Security headers middleware
  - Request ID middleware

#### `core/dependencies.py`
- **Cel**: Wspólne dependencies dla wszystkich modułów
- **Zawartość**:
  - Database session dependency
  - Current user dependency
  - Permission checking dependencies
  - Pagination dependencies
  - Common query parameters

#### `core/logging.py`
- **Cel**: Konfiguracja systemu logowania
- **Zawartość**:
  - Structured logging setup
  - Log formatters
  - Log handlers configuration
  - Request/response logging
  - Error tracking integration

### 1.2 Struktura modułów biznesowych

Każdy moduł w `modules/` będzie miał standardową strukturę:

#### `modules/{module_name}/models.py`
- SQLAlchemy models
- Pydantic models (jeśli potrzebne)
- Model relationships
- Database constraints

#### `modules/{module_name}/schemas.py`
- Request schemas (Pydantic)
- Response schemas (Pydantic)
- Validation schemas
- Serialization schemas

#### `modules/{module_name}/services.py`
- Business logic layer
- Service classes/functions
- Transaction management
- External API calls

#### `modules/{module_name}/repositories.py`
- Data access layer
- CRUD operations
- Query builders
- Database-specific logic

#### `modules/{module_name}/endpoints.py`
- FastAPI APIRouter
- Route handlers
- Request/response handling
- Error handling

### 1.3 Moduł `common/`

#### `common/utils.py`
- Helper functions
- Date/time utilities
- JSON parsing utilities
- String manipulation
- File operations

#### `common/validators.py`
- Email validation
- Phone number validation
- Password strength validation
- Custom business validators

#### `common/constants.py`
- Application constants
- Error codes
- Status codes
- Configuration constants

### 1.4 Moduł `clients/`

#### `clients/kafka_client.py`
- Kafka producer/consumer singleton
- Message serialization
- Error handling
- Connection management

#### `clients/redis_client.py`
- Redis connection singleton
- Caching utilities
- Session management
- Pub/Sub functionality

#### `clients/stripe_client.py`
- Stripe API client
- Payment processing
- Webhook handling
- Error handling

## 2. Implementacja CLI Commands

### 2.1 Nowe komendy CLI

#### `init` - Inicjalizacja projektu
```bash
fastapi-registry init [project_name] [--template=basic|full]
```

**Funkcjonalność**:
- Tworzenie struktury katalogów
- Generowanie plików core/
- Tworzenie main.py
- Konfiguracja pyproject.toml
- Tworzenie .env.example
- Inicjalizacja git repository

#### `scaffold core` - Generowanie core modułów
```bash
fastapi-registry scaffold core [--force]
```

**Funkcjonalność**:
- Generowanie wszystkich plików w core/
- Aktualizacja istniejących plików (z potwierdzeniem)
- Konfiguracja middleware
- Ustawienie dependencies

#### `add module` - Dodawanie modułu biznesowego
```bash
fastapi-registry add module <module_name> [--template=auth|users|custom]
```

**Funkcjonalność**:
- Tworzenie struktury modułu
- Generowanie wszystkich plików modułu
- Rejestracja w main.py
- Aktualizacja dependencies

### 2.2 Rozszerzenie istniejących komend

#### `list` - Rozszerzenie o kategorie
```bash
fastapi-registry list [--category=core|modules|all]
```

#### `info` - Informacje o module/projekcie
```bash
fastapi-registry info <module_name>
fastapi-registry info project
```

## 3. Struktura Template'ów

### 3.1 Template Core
```
templates/core/
├── config.py.template
├── factory.py.template
├── middlewares.py.template
├── dependencies.py.template
└── logging.py.template
```

### 3.2 Template Modułu
```
templates/module/
├── models.py.template
├── schemas.py.template
├── services.py.template
├── repositories.py.template
└── endpoints.py.template
```

### 3.3 Template Projektu
```
templates/project/
├── basic/
│   ├── main.py.template
│   ├── pyproject.toml.template
│   └── .env.example.template
└── full/
    ├── main.py.template
    ├── pyproject.toml.template
    ├── .env.example.template
    ├── docker-compose.yml.template
    └── Dockerfile.template
```

## 4. Implementacja Krok po Kroku

### Faza 1: Przygotowanie infrastruktury
1. **Rozszerzenie CLI** - dodanie nowych komend
2. **Template system** - system generowania plików z template'ów
3. **Project detection** - wykrywanie istniejących projektów FastAPI
4. **File operations** - bezpieczne operacje na plikach

### Faza 2: Core scaffolding
1. **Template'y core** - przygotowanie template'ów dla core/
2. **Command `scaffold core`** - implementacja generowania core
3. **Integration testing** - testy integracyjne core

### Faza 3: Module scaffolding
1. **Template'y modułów** - przygotowanie template'ów dla modułów
2. **Command `add module`** - implementacja dodawania modułów
3. **Module registration** - automatyczna rejestracja w main.py

### Faza 4: Project initialization
1. **Template'y projektów** - przygotowanie template'ów projektów
2. **Command `init`** - implementacja inicjalizacji projektu
3. **Project structure** - generowanie pełnej struktury

### Faza 5: Advanced features
1. **Configuration merging** - inteligentne łączenie konfiguracji
2. **Dependency management** - automatyczne zarządzanie dependencies
3. **Migration support** - wsparcie dla migracji bazy danych
4. **Testing integration** - generowanie testów

## 5. Szczegóły Techniczne

### 5.1 Template Engine
- Użycie Jinja2 do renderowania template'ów
- Support dla zmiennych i warunków
- Template inheritance
- Custom filters i functions

### 5.2 Configuration Management
- Pydantic Settings dla konfiguracji
- Environment variables support
- Nested configuration classes
- Validation i type checking

### 5.3 File Operations
- Atomic file operations
- Backup przed modyfikacją
- Conflict resolution
- Path validation

### 5.4 Error Handling
- Graceful error handling
- User-friendly error messages
- Rollback capabilities
- Detailed logging

## 6. Przykłady Użycia

### 6.1 Inicjalizacja nowego projektu
```bash
# Podstawowy projekt
fastapi-registry init my-project

# Pełny projekt z Docker
fastapi-registry init my-project --template=full
```

### 6.2 Generowanie core
```bash
# Generowanie core w istniejącym projekcie
fastapi-registry scaffold core

# Wymuszenie nadpisania
fastapi-registry scaffold core --force
```

### 6.3 Dodawanie modułów
```bash
# Dodanie modułu auth
fastapi-registry add module auth

# Dodanie modułu users
fastapi-registry add module users

# Dodanie custom modułu
fastapi-registry add module billing --template=custom
```

## 7. Testowanie

### 7.1 Unit Tests
- Testy dla każdego CLI command
- Testy dla template rendering
- Testy dla file operations
- Testy dla configuration management

### 7.2 Integration Tests
- Testy end-to-end dla każdego workflow
- Testy na przykładowych projektach
- Testy kompatybilności z różnymi wersjami FastAPI

### 7.3 Manual Testing
- Testy na różnych systemach operacyjnych
- Testy z różnymi konfiguracjami
- Testy performance

## 8. Dokumentacja

### 8.1 User Documentation
- README z przykładami użycia
- Tutorial krok po kroku
- FAQ i troubleshooting
- Video tutorials

### 8.2 Developer Documentation
- API documentation
- Architecture overview
- Contributing guidelines
- Code examples

## 9. Roadmap

### Q1 2024
- Faza 1-2: Infrastruktura i core scaffolding
- Podstawowe CLI commands
- Template system

### Q2 2024
- Faza 3-4: Module scaffolding i project initialization
- Pełna funkcjonalność scaffolding
- Dokumentacja

### Q3 2024
- Faza 5: Advanced features
- Performance optimization
- Community feedback integration

### Q4 2024
- Stabilizacja
- Dodatkowe template'y
- Ecosystem integration

## 10. Metryki Sukcesu

- Liczba pobrań i użyć CLI
- Liczba wygenerowanych projektów
- Feedback od społeczności
- Czas generowania projektu (< 30 sekund)
- Jakość wygenerowanego kodu (linting, testing)

---

*Ten plan będzie aktualizowany w miarę postępu implementacji i feedbacku od społeczności.*