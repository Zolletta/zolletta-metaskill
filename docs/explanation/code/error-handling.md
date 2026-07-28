---
audience: human, ai
status: stable
skills: [patterns, review, python-*, php-*]
---
# Error Handling (Language-Agnostic)

> Four rules adapted from [php-best-practices](https://skills.sh/php-community/php-best-practices) (MIT, v2.1.0). Examples in PHP and Python. The principles apply identically regardless of language.

## 1. Custom exceptions

Create specific exception classes instead of using generic base exceptions. This lets callers catch exactly the error they can handle.

```php
// BAD: generic exception
throw new \Exception("User not found");

// GOOD: specific exception
class UserNotFoundException extends \RuntimeException {}
throw new UserNotFoundException("User {$id} not found");
```

```python
# BAD: generic exception
raise Exception("User not found")

# GOOD: specific exception
class UserNotFoundError(RuntimeError):
    pass

raise UserNotFoundError(f"User {user_id} not found")
```

## 2. Exception hierarchy

Organize exceptions into a meaningful hierarchy: domain → subdomain → specific. This lets callers catch at the level of abstraction they care about.

```php
// Domain → subdomain → specific
namespace App\Exceptions;

class DomainException extends \RuntimeException {}           // domain
class ValidationException extends DomainException {}          // subdomain
class InvalidEmailException extends ValidationException {}    // specific
class InvalidPasswordException extends ValidationException {} // specific

// Caller can catch at any level:
try {
    $service->register($email, $password);
} catch (InvalidEmailException $e) {
    // handle only invalid email
} catch (ValidationException $e) {
    // handle any validation error
} catch (DomainException $e) {
    // handle any domain error
}
```

```python
# Domain → subdomain → specific
class DomainError(RuntimeError): ...
class ValidationError(DomainError): ...
class InvalidEmailError(ValidationError): ...
class InvalidPasswordError(ValidationError): ...

# Caller can catch at any level:
try:
    service.register(email, password)
except InvalidEmailError:
    # handle only invalid email
except ValidationError:
    # handle any validation error
except DomainError:
    # handle any domain error
```

## 3. Catch specific exceptions

Catch specific exception types, not the generic base class. Catching the base class swallows unexpected errors and hides bugs.

```php
// BAD: catches everything
try {
    $user = $repo->find($id);
} catch (\Exception $e) {
    $user = null;  // also swallows TypeError, OutOfMemoryError, etc.
}

// GOOD: catches only the expected exception
try {
    $user = $repo->find($id);
} catch (UserNotFoundException $e) {
    $user = null;
}
```

```python
# BAD: catches everything
try:
    user = repo.find(user_id)
except Exception:
    user = None  # also swallows TypeError, KeyError, etc.

# GOOD: catches only the expected exception
try:
    user = repo.find(user_id)
except UserNotFoundError:
    user = None
```

## 4. Finally for cleanup

Use `finally` for guaranteed resource cleanup — it runs whether the `try` block succeeds or throws.

```php
$lock = $lockManager->acquire($key);
try {
    $result = $service->process($data);
} catch (ProcessingException $e) {
    $logger->error("Processing failed", ["exception" => $e]);
    $result = null;
} finally {
    $lock->release();  // always runs
}
```

```python
lock = lock_manager.acquire(key)
try:
    result = service.process(data)
except ProcessingError as e:
    logger.error("Processing failed", exc_info=e)
    result = None
finally:
    lock.release()  # always runs
```

## 5. Wrap library exceptions in domain exceptions

Catch low-level or library-specific exceptions at the boundary where they originate and re-throw them as domain exceptions, preserving the original message and (where the language supports it) the cause. This composes rules 1 and 3: callers depend on a stable domain exception type (rule 1) and are never forced to catch the generic base (rule 3) just to handle a library failure.

The pattern has three parts:

1. **Catch the specific library exception** — never the generic base.
2. **Re-throw a domain exception** that names the domain concept, not the library.
3. **Preserve the cause** so the original failure is traceable in stack traces.

```php
<?php

// Library throws ExpiredException (e.g. from a JWT library)
try {
    $token = $this->tokenParser->parse($raw);
} catch (ExpiredException $e) {
    // Wrap in a domain exception — callers depend on ExpiredAuthTokenException,
    // not on the library's ExpiredException
    throw new ExpiredAuthTokenException('Il token fornito è scaduto', previous: $e);
} catch (\Exception $e) {
    throw new SecurityException("Token validation failed: {$e->getMessage()}", previous: $e);
}
```

```python
# Library raises a low-level error (e.g. from an HTTP client or file parser)
try:
    data = httpx.get(url).json()
except httpx.HTTPError as e:
    # Wrap in a domain exception — callers catch GitLabFetchError, not httpx.HTTPError
    raise GitLabFetchError(f"Failed to fetch from GitLab -> {e}") from e
except KeyError as e:
    raise ConfigParseError(f"Missing required config key -> {e}") from e
```

**Why this matters**:

- **Stable caller contracts**: callers depend on `ExpiredAuthTokenException` / `GitLabFetchError`, not on `firebase.jwt.ExpiredException` / `httpx.HTTPError`. Swapping the library does not break every `except` clause in the codebase.
- **Domain vocabulary in stack traces**: the exception names the *domain concept* that failed, not the *library* that raised. A production stack trace reading `SecurityException: token validation failed` is actionable; `ExpiredException` is not.
- **Cause preservation**: `from e` (Python) / `previous: $e` (PHP) keeps the original exception in the chain, so debugging still reaches the library layer.

**Violation signals**:

- Library exception types (`httpx.HTTPError`, `redis.ConnectionError`, `ExpiredException`) leaking past a service boundary into caller code.
- `except Exception as e: raise RuntimeError(str(e))` — wraps but loses the cause chain (Python: missing `from e`).
- Domain exceptions without a `previous` / `from` link to the original — the chain is broken and the root cause is unrecoverable.

**Boundary definition**: the wrapping happens at the *service boundary* — the class or module that owns the integration with the library. Code *inside* the service may use the library's exceptions; code *outside* the service should only see domain exceptions.
