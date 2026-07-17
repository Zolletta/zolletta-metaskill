# General Principles (Language-Agnostic)

> Adapted from [python-design-patterns](https://github.com/wshobson/agents) by wshobson (MIT License). Examples in Python and PHP. The principles apply identically regardless of language.

## SOLID Principles

### 1. Single Responsibility (SRP)

Each class or function should have one reason to change. Separate concerns into focused components.

```python
# BAD: Handler does everything
class UserHandler:
    async def create_user(self, request: Request) -> Response:
        data = await request.json()           # HTTP parsing
        if not data.get("email"):             # Validation
            return Response({"error": "email required"}, status=400)
        user = await db.execute(              # Database access
            "INSERT INTO users (email, name) VALUES ($1, $2) RETURNING *",
            data["email"], data["name"]
        )
        return Response({"id": user.id}, status=201)  # Response formatting

# GOOD: Separated concerns
class UserService:
    """Business logic only."""
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo
    async def create_user(self, data: CreateUserInput) -> User:
        user = User(email=data.email, name=data.name)
        return await self._repo.save(user)

class UserHandler:
    """HTTP concerns only."""
    def __init__(self, service: UserService) -> None:
        self._service = service
    async def create_user(self, request: Request) -> Response:
        data = CreateUserInput(**(await request.json()))
        user = await self._service.create_user(data)
        return Response(user.to_dict(), status=201)
```

```php
// BAD: Controller does everything
class UserController {
    public function create(Request $request): Response {
        $data = $request->json();                    // HTTP parsing
        if (empty($data['email'])) {                 // Validation
            return new Response(['error' => 'email required'], 400);
        }
        $user = DB::insert('users', $data);          // DB access
        return new Response(['id' => $user->id], 201); // Formatting
    }
}

// GOOD: Separated concerns
class UserService {
    public function __construct(private UserRepository $repo) {}
    public function createUser(array $data): User {
        $user = new User($data['email'], $data['name']);
        return $this->repo->save($user);
    }
}
class UserController {
    public function __construct(private UserService $service) {}
    public function create(Request $request): Response {
        $user = $this->service->createUser($request->json());
        return new Response($user->toArray(), 201);
    }
}
```

### 2. Open/Closed (OCP)

Software entities should be open for extension, but closed for modification. Adding a new type should not require editing existing code — use polymorphism (strategy pattern, plugin registry, protocol-based dispatch) instead of if/elif type ladders.

**Violation signal**: if/elif isinstance ladders, match/case on type, or getattr string dispatch. Each new type requires adding a branch.

```python
# BAD: adding a new type requires editing this function
def process_pipeline(pipeline):
    if pipeline.type == "feature_branch":
        ...
    elif pipeline.type == "protected_branch":
        ...
    elif pipeline.type == "mr":
        ...

# GOOD: strategy pattern — adding a type = new class + register, no modification
class PipelineType(Protocol):
    def run(self) -> None: ...

PIPELINE_TYPES: dict[str, type[PipelineType]] = {}

def register(name: str):
    def decorator(cls):
        PIPELINE_TYPES[name] = cls
        return cls
    return decorator

@register("feature_branch")
class FeatureBranchPipeline:
    def run(self) -> None: ...
```

**Manual detection** (without AST scripts):

```bash
# PHP: find if/elseif chains with instanceof or get_class
grep -rn "instanceof\|get_class(" src/ --include="*.php" | head -20
```

### 3. Liskov Substitution (LSP)

Subtypes must be substitutable for their base types. If code expects a parent class, passing a subclass must not break it.

**Violation signals**:

- Subclass method requires more parameters than parent (narrower precondition)
- Subclass method raises new exception types not raised by parent
- Subclass overrides a method with `pass` or `return None` (weakens postcondition)
- Subclass accepts fewer parameters than parent (can't handle all calls)

```python
# BAD: extra required param — callers passing only `data` break
class BaseValidator:
    def validate(self, data: dict) -> bool: ...

class StrictValidator(BaseValidator):
    def validate(self, data: dict, strict_mode: bool = True) -> bool: ...

# GOOD: same signature, strict mode is internal configuration
class StrictValidator(BaseValidator):
    def validate(self, data: dict) -> bool: ...
```

### 4. Interface Segregation (ISP)

Clients should not be forced to depend on interfaces they do not use. Fat protocols with many methods force implementers to stub or raise NotImplementedError for methods they don't need.

```python
# BAD: fat protocol forces stubs
class FatProtocol(Protocol):
    def read(self) -> bytes: ...
    def write(self, data: bytes) -> None: ...
    def delete(self, key: str) -> None: ...
    def list_keys(self) -> list[str]: ...
    def compress(self) -> None: ...

class ReadOnlyImpl(FatProtocol):
    def read(self) -> bytes: ...
    def write(self, data: bytes) -> None:
        raise NotImplementedError  # ISP violation
    def delete(self, key: str) -> None:
        raise NotImplementedError  # ISP violation

# GOOD: segregated protocols
class Readable(Protocol):
    def read(self) -> bytes: ...

class Writable(Protocol):
    def write(self, data: bytes) -> None: ...

class ReadOnlyImpl(Readable):
    def read(self) -> bytes: ...
    # No stubs needed — only implements what it uses
```

### 5. Dependency Inversion (DIP)

High-level modules should not depend on low-level modules; both should depend on abstractions. Dependencies should be **passed in** (injected), not **created internally**. The composition root (main, CLI entry point) is the only place where object creation belongs.

```python
# BAD: creates its own dependencies
class Orchestrator:
    def __init__(self, config: Config):
        self.gitlab_client = GitLabClient(config.url, config.token)  # DIP violation
        self.cache = Cache(config.cache_dir)                         # DIP violation

# GOOD: dependencies injected
class Orchestrator:
    def __init__(self, config: Config, gitlab_client: GitLabClient, cache: Cache):
        self.config = config
        self.gitlab_client = gitlab_client
        self.cache = cache

# Composition root (entry point — the ONLY place that creates objects):
def main():
    config = Config(...)
    gitlab_client = GitLabClient(config.url, config.token)
    cache = Cache(config.cache_dir)
    orchestrator = Orchestrator(config, gitlab_client, cache)
```

**Exceptions (not violations)**: entry points / composition roots, dataclasses/NamedTuples/TypedDicts/Enums, factory classes, value objects with no external service calls.

**Manual detection** (without AST scripts):

```bash
# PHP: find internal dependency creation in class constructors
grep -rn "new \|->.* = new " src/ --include="*.php" | grep -v "Factory\|Builder"
```

## Other Fundamental Principles

### KISS (Keep It Simple)

Before adding complexity, ask: does a simpler solution work?

```python
# Over-engineered: Factory with registration
class OutputFormatterFactory:
    _formatters: dict[str, type[Formatter]] = {}
    @classmethod
    def register(cls, name: str): ...
    @classmethod
    def create(cls, name: str) -> Formatter: ...

# Simple: Just use a dictionary
FORMATTERS = {"json": JsonFormatter, "csv": CsvFormatter, "xml": XmlFormatter}
def get_formatter(name: str) -> Formatter:
    return FORMATTERS[name]()
```

The factory pattern adds code without adding value here. Save patterns for when they solve real problems.

### Separation of Concerns

Organize code into distinct layers with clear responsibilities.

```text
+-----------------------------------------------------+
|  API Layer (handlers / controllers)                 |
|  - Parse requests, call services, format responses  |
+-----------------------------------------------------+
                        |
+-----------------------------------------------------+
|  Service Layer (business logic)                     |
|  - Domain rules, validation, orchestration          |
+-----------------------------------------------------+
                        |
+-----------------------------------------------------+
|  Repository Layer (data access)                     |
|  - SQL queries, external API calls, cache           |
+-----------------------------------------------------+
```

Each layer depends only on layers below it. See the SRP examples above for Python and PHP implementations of this layering.

### Composition Over Inheritance

Build behavior by combining objects rather than inheriting.

```python
# Inheritance: Rigid and hard to test
class EmailNotificationService(NotificationService):
    def __init__(self):
        super().__init__()
        self._smtp = SmtpClient()  # Hard to mock

# Composition: Flexible and testable
class NotificationService:
    def __init__(self, email_sender: EmailSender, sms_sender: SmsSender | None = None):
        self._email = email_sender
        self._sms = sms_sender

# Easy to test with fakes
service = NotificationService(email_sender=FakeEmailSender(), sms_sender=FakeSmsSender())
```

**When composition produces deeply nested wrappers**: keep the composition shallow (2-3 levels). If wrapping is the only mechanism, consider whether a Protocol-based approach or simple function composition would be cleaner than a chain of decorator objects.

```php
// Composition with constructor promotion
class NotificationService {
    public function __construct(
        private EmailSender $email,
        private ?SmsSender $sms = null,
    ) {}
    public function notify(User $user, string $message): void {
        $this->email->send($user->email, $message);
        if ($this->sms && $user->phone) {
            $this->sms->send($user->phone, $message);
        }
    }
}
```

### Rule of Three

Wait until you have three instances before abstracting. Duplication is often better than the wrong abstraction.

```python
# Two similar functions? Don't abstract yet
def process_orders(orders: list[Order]) -> list[Result]: ...
def process_returns(returns: list[Return]) -> list[Result]: ...

# These look similar, but different validation, different processing, different errors.
# Duplication is often better than the wrong abstraction.
# Only after a third case, consider if there's a real pattern.
```

### Function Size Guidelines

Keep functions focused. Extract when a function:

- Exceeds 20-50 lines (varies by complexity)
- Serves multiple distinct purposes
- Has deeply nested logic (3+ levels)

```python
# Too long, multiple concerns mixed
def process_order(order: Order) -> Result:
    # 50 lines of validation...
    # 30 lines of inventory check...
    # 40 lines of payment processing...
    # 20 lines of notification...
    pass

# Better: Composed from focused functions
def process_order(order: Order) -> Result:
    validate_order(order)
    reserve_inventory(order)
    payment_result = charge_payment(order)
    send_confirmation(order, payment_result)
    return Result(success=True, order_id=order.id)
```

## Dependency Injection

Pass dependencies through constructors for testability. This is the mechanism that implements DIP.

```python
from typing import Protocol

class Logger(Protocol):
    def info(self, msg: str, **kwargs) -> None: ...
    def error(self, msg: str, **kwargs) -> None: ...

class Cache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl: int) -> None: ...

class UserService:
    def __init__(self, repository: UserRepository, cache: Cache, logger: Logger) -> None:
        self._repo = repository
        self._cache = cache
        self._logger = logger

# Production
service = UserService(repository=PostgresUserRepository(db), cache=RedisCache(redis), logger=StructlogLogger())
# Testing
service = UserService(repository=InMemoryUserRepository(), cache=FakeCache(), logger=NullLogger())
```

## God Class Detection

A **God class** is not defined by size (lines, methods, attributes). It is defined by **having multiple reasons to change from different domains**.

### Procedure

1. List every change that could require editing the class.
2. Group the changes by domain (HTTP parsing, business rules, data access, formatting, configuration, I/O).
3. If the list has items from **different domains**, the class is a God class — split it.
4. If all changes stem from the **same domain**, the class may be appropriately sized even if it is long.

**Manual triage** (when AST scripts are unavailable — e.g. PHP, Java):

```bash
# Find large class files
find src/ -name "*.php" -exec wc -l {} + | sort -rn | head -20

# Count methods per class (rough)
grep -c "public function\|private function\|protected function" src/MyClass.php
```

### Domain reference table

| Domain         | Examples                                           |
| -------------- | -------------------------------------------------- |
| HTTP/API       | request parsing, response formatting, status codes |
| Business logic | validation, domain rules, calculations             |
| Data access    | SQL, ORM calls, cache reads/writes                 |
| Configuration  | env vars, config dicts, defaults                   |
| Presentation   | markdown/HTML generation, table formatting, emoji  |
| I/O            | file reads/writes, network calls, temp files       |

### Symptoms (not proofs)

- **7+ constructor parameters** — suggests too many responsibilities, not a DI problem.
- **Methods from different layers** — API parsing + business logic + DB access + formatting.
- **I/O mixed with business logic** — SQL/HTTP calls embedded in domain rules.
- **High attribute count** — many `self.*` / `$this->` attributes suggest state for multiple concerns.

### What is NOT a God class

- A large class whose methods all serve one domain (e.g., a parser with 14 handler methods).
- A class with many static helpers that all operate on the same data structure.
- An orchestrator that delegates to injected dependencies (high attribute count is delegation, not mixed concerns).

## Common Anti-Patterns

**Don't expose internal types:**

```python
# BAD: Leaking ORM model to API
@app.get("/users/{id}")
def get_user(id: str) -> UserModel:  # SQLAlchemy model
    return db.query(UserModel).get(id)

# GOOD: Use response schemas
@app.get("/users/{id}")
def get_user(id: str) -> UserResponse:
    user = db.query(UserModel).get(id)
    return UserResponse.from_orm(user)
```

**Don't mix I/O with business logic:**

```python
# BAD: SQL embedded in business logic
def calculate_discount(user_id: str) -> float:
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)
    orders = db.query("SELECT * FROM orders WHERE user_id = ?", user_id)
    # Business logic mixed with data access

# GOOD: Repository pattern
def calculate_discount(user: User, order_history: list[Order]) -> float:
    # Pure business logic, easily testable
    if len(order_history) > 10:
        return 0.15
    return 0.0
```
