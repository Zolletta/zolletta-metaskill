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
