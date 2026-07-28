---
audience: human, ai
status: stable
skills: [patterns, review, python-*, php-*]
---
# Error Handling (Language-Agnostic)

> Five rules adapted from [php-best-practices](https://skills.sh/php-community/php-best-practices) (MIT, v2.1.0). Examples in PHP and Python. The principles apply identically regardless of language.

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

**Why this matters**: callers catch exactly the error they can handle. See [Python user-defined exceptions](https://docs.python.org/3/tutorial/errors.html#user-defined-exceptions), [PHP extending exceptions](https://www.php.net/manual/en/language.exceptions.extending.php).

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

**Why this matters**: callers catch at the level of abstraction they care about. See [Python exception hierarchy](https://docs.python.org/3/library/exceptions.html#exception-hierarchy).

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

**Why this matters**: catching the base class swallows unexpected errors and hides bugs. See [Python handling exceptions](https://docs.python.org/3/tutorial/errors.html#handling-exceptions).

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

**Why this matters**: `finally` runs whether the `try` succeeds or throws — guaranteed cleanup. See [Python try statement](https://docs.python.org/3/reference/compound_stmts.html#the-try-statement), [PHP exceptions](https://www.php.net/manual/en/language.exceptions.php).

## 5. Wrap library exceptions in domain exceptions

Catch library-specific exceptions at the service boundary and re-throw as domain exceptions, preserving the cause. This composes rules 1 and 3: callers depend on a stable domain type and never catch the library's base exception.

```php
<?php

// Library throws ExpiredException (e.g. from a JWT library)
try {
    $token = $this->tokenParser->parse($raw);
} catch (ExpiredException $e) {
    throw new ExpiredAuthTokenException('Il token fornito è scaduto', previous: $e);
}
```

```python
# Library raises httpx.HTTPError
try:
    data = httpx.get(url).json()
except httpx.HTTPError as e:
    raise GitLabFetchError(f"Failed to fetch -> {e}") from e
```

**Why this matters**: swapping the library does not break every `except` clause; the cause chain (`from e` / `previous: $e`) keeps the root failure traceable. See [PEP 3134](https://peps.python.org/pep-3134/) (Python exception chaining), [PHP Exception::__construct](https://www.php.net/manual/en/exception.construct.php) (`previous` parameter).
