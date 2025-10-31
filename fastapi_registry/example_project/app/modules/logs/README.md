# Logs Module

Comprehensive logging module for FastAPI applications with database storage, automatic error tracking, and REST API for log management.

## Features

- **Database Storage**: Store logs in PostgreSQL or SQLite
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Automatic Error Logging**: Decorator that catches and logs exceptions
- **Request Tracing**: Track logs by request ID
- **User Activity Tracking**: Associate logs with user IDs
- **REST API**: Full CRUD operations for log management
- **Automatic Cleanup**: Delete old logs with retention policies

## Installation

The module is already installed as part of the `fastapi_registry` example project.

## Database Setup

Configure your database connection in `.env`:

```bash
# For development (SQLite)
DATABASE_URL=sqlite+aiosqlite:///./dev.db

# For production (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

## Usage

### 1. Using the Error Logging Decorator

The `@log_errors` decorator automatically catches and logs exceptions:

```python
from app.modules.logs.decorators import log_errors
from app.modules.logs.service import LogService

@log_errors(message="Failed to process user data")
async def process_user(
    user_id: str,
    log_service: LogService  # Decorator will auto-detect this
):
    # Your code here
    result = await some_risky_operation(user_id)
    return result
```

**Decorator Options:**

```python
@log_errors(
    message="Custom error message",  # Optional custom message
    reraise=True,  # Re-raise exception after logging (default: True)
    level=LogLevel.ERROR  # Log level (default: ERROR)
)
async def my_function():
    pass
```

### 2. Using LogService Directly

For manual logging:

```python
from fastapi import Depends
from app.modules.logs.service import LogService
from app.modules.logs.repositories import get_log_repository

@router.post("/users")
async def create_user(
    user_data: UserCreate,
    repo = Depends(get_log_repository)
):
    log_service = LogService(repo)

    try:
        user = create_user_in_db(user_data)

        # Log successful operation
        await log_service.log_info(
            message=f"User {user.id} created successfully",
            module="users",
            function="create_user",
            user_id=current_user.id
        )

        return user
    except Exception as e:
        # Log error with full traceback
        await log_service.log_error(
            message="Failed to create user",
            exception=e,
            module="users",
            function="create_user",
            user_id=current_user.id,
            extra_data=str(user_data)
        )
        raise
```

### 3. Using the Repository Directly

For low-level database operations:

```python
from fastapi import Depends
from app.modules.logs.repositories import LogRepository, get_log_repository
from app.modules.logs.db_models import LogLevel

@router.get("/process")
async def process_data(
    repo: LogRepository = Depends(get_log_repository)
):
    # Create log entry
    await repo.create_log(
        level=LogLevel.INFO,
        message="Processing started",
        module="data_processor",
        function="process_data"
    )
```

## API Endpoints

Mount the router in your main application:

```python
from fastapi import FastAPI
from app.modules.logs.router import router as logs_router

app = FastAPI()
app.include_router(logs_router, prefix="/api/v1/logs", tags=["logs"])
```

### Available Endpoints

#### Create Log Entry
```http
POST /api/v1/logs
Content-Type: application/json

{
  "level": "ERROR",
  "message": "Something went wrong",
  "module": "users",
  "userId": "user_123"
}
```

#### List Logs with Filters
```http
GET /api/v1/logs?level=ERROR&userId=user_123&limit=50
```

Query parameters:
- `skip`: Number of records to skip (pagination)
- `limit`: Max records to return (1-1000)
- `level`: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `user_id`: Filter by user ID
- `request_id`: Filter by request ID
- `module`: Filter by module name
- `start_date`: Filter logs after this date
- `end_date`: Filter logs before this date

#### Get Error Logs Only
```http
GET /api/v1/logs/errors?limit=100
```

#### Get Logs by Request ID
```http
GET /api/v1/logs/request/req_abc123
```

#### Get Specific Log
```http
GET /api/v1/logs/{log_id}
```

#### Cleanup Old Logs
```http
DELETE /api/v1/logs/cleanup?days=30
```

Deletes logs older than specified number of days.

## Advanced Usage

### Request Tracing

Add request ID to all logs in a request lifecycle:

```python
from fastapi import Request
import uuid

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    return response

# The decorator will automatically extract request_id from Request object
@log_errors()
async def my_endpoint(request: Request):
    # request.state.request_id will be used automatically
    pass
```

### User Tracking

The decorator automatically extracts user information from:
- `user_id` parameter
- `current_user` parameter (if it has `id` attribute)
- `Request.state.user` (if available)

```python
@log_errors()
async def my_endpoint(current_user: User = Depends(get_current_user)):
    # current_user.id will be used automatically
    pass
```

### Scheduled Log Cleanup

Set up automatic cleanup of old logs:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.modules.logs.service import LogService

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=2)  # Run at 2 AM
async def cleanup_old_logs():
    repo = LogRepository(db)
    service = LogService(repo)
    deleted = await service.cleanup_old_logs(days=30)
    print(f"Deleted {deleted} old logs")

scheduler.start()
```

## Database Models

### LogDB (SQLAlchemy Model)

```python
class LogDB:
    id: str              # ULID identifier
    level: str           # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message: str         # Log message
    module: str          # Module/file name
    function: str        # Function name
    user_id: str         # User ID (optional)
    request_id: str      # Request ID (optional)
    traceback: str       # Full exception traceback (optional)
    extra_data: str      # Additional data (optional)
    created_at: datetime # Timestamp
```

### Indexes

The table has the following indexes for query optimization:
- `level` (for filtering by log level)
- `user_id` (for filtering by user)
- `request_id` (for request tracing)
- `created_at` (for date-based queries)
- Composite: `(level, created_at)`
- Composite: `(user_id, created_at)`

## Best Practices

1. **Use Appropriate Log Levels**
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General informational messages
   - `WARNING`: Warning messages for potentially harmful situations
   - `ERROR`: Error events that might still allow app to continue
   - `CRITICAL`: Very severe error events

2. **Add Context to Logs**
   ```python
   await log_service.log_error(
       message="Failed to process payment",
       user_id=user.id,
       request_id=request_id,
       extra_data=json.dumps({
           "amount": payment.amount,
           "currency": payment.currency,
           "payment_method": payment.method
       })
   )
   ```

3. **Regular Cleanup**
   - Schedule automatic deletion of old logs
   - Adjust retention period based on compliance requirements
   - Consider archiving critical logs before deletion

4. **Monitor Error Rates**
   - Use the `/api/v1/logs/errors` endpoint to track error trends
   - Set up alerts for increased error rates
   - Review recent errors regularly

## Testing

Test the decorator:

```python
import pytest
from app.modules.logs.decorators import log_errors
from app.modules.logs.service import LogService

@pytest.mark.asyncio
async def test_log_errors_decorator(log_service: LogService):
    @log_errors(message="Test error", reraise=False)
    async def failing_function(log_service: LogService):
        raise ValueError("Test exception")

    # Should not raise, just log
    await failing_function(log_service=log_service)

    # Verify log was created
    errors = await log_service.get_recent_errors(limit=1)
    assert len(errors) > 0
    assert "Test error" in errors[0].message
```

## Configuration

No additional configuration is required. The module uses the application's database connection defined in `DATABASE_URL`.

## Troubleshooting

### Logs not appearing in database

1. Check database connection
2. Ensure `LogDB` table exists (run migrations)
3. Verify `log_service` is passed to decorated functions
4. Check application logs for errors

### Decorator not working

1. Ensure function is async if decorated function is async
2. Pass `log_service` parameter to function
3. Check that exception is actually being raised

### Performance concerns

1. Use appropriate indexes (already configured)
2. Set up regular cleanup of old logs
3. Consider async writes for high-traffic applications
4. Use log level filtering to reduce volume
