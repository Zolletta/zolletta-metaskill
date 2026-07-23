---
audience: human, ai
status: stable
skills: [patterns, review, python-*, php-*]
---
# Performance (Language-Agnostic)

> Two rules adapted from [php-best-practices](https://skills.sh/php-community/php-best-practices) (MIT, v2.1.0). Examples in PHP and Python. The principles apply identically regardless of language.

## 1. Lazy loading

Defer expensive operations until they are actually needed. This avoids paying the cost for code paths that never execute.

```php
// BAD: always loads all data, even if only one field is used
class UserDTO {
    public function __construct(
        private readonly int $id,
        private readonly string $name,
        private readonly string $email,
        private readonly array $preferences,  // expensive to load
        private readonly array $permissions,  // expensive to load
    ) {}
}

// GOOD: lazy-load expensive fields
class UserDTO {
    private ?array $preferences = null;
    private ?array $permissions = null;

    public function __construct(
        private readonly int $id,
        private readonly string $name,
        private readonly string $email,
        private readonly PreferenceRepository $prefRepo,
        private readonly PermissionRepository $permRepo,
    ) {}

    public function getPreferences(): array {
        return $this->preferences ??= $this->prefRepo->loadForUser($this->id);
    }

    public function getPermissions(): array {
        return $this->permissions ??= $this->permRepo->loadForUser($this->id);
    }
}
```

```python
# BAD: always loads all data, even if only one field is used
class UserDTO:
    def __init__(self, user_id, name, email, preferences, permissions):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.preferences = preferences    # expensive to load
        self.permissions = permissions    # expensive to load

# GOOD: lazy-load expensive fields
from functools import cached_property

class UserDTO:
    def __init__(self, user_id, name, email, pref_repo, perm_repo):
        self.user_id = user_id
        self.name = name
        self.email = email
        self._pref_repo = pref_repo
        self._perm_repo = perm_repo

    @cached_property
    def preferences(self) -> dict:
        return self._pref_repo.load_for_user(self.user_id)

    @cached_property
    def permissions(self) -> dict:
        return self._perm_repo.load_for_user(self.user_id)
```

## 2. Generators

Use generators for large datasets to avoid loading everything into memory at once. Both PHP and Python support `yield`.

```php
// BAD: loads all rows into memory
function getAllUsers(): array {
    $users = [];
    foreach ($db->query("SELECT * FROM users") as $row) {
        $users[] = $row;
    }
    return $users;  // could be millions of rows
}

// GOOD: generator yields one row at a time
function getAllUsers(): \Generator {
    foreach ($db->query("SELECT * FROM users") as $row) {
        yield $row;
    }
}

// Consumer memory stays flat regardless of dataset size
foreach (getAllUsers() as $user) {
    $exporter->write($user);
}
```

```python
# BAD: loads all rows into memory
def get_all_users() -> list[dict]:
    return db.query("SELECT * FROM users")  # could be millions of rows

# GOOD: generator yields one row at a time
def get_all_users() -> Iterator[dict]:
    for row in db.query("SELECT * FROM users"):
        yield row

# Consumer memory stays flat regardless of dataset size
for user in get_all_users():
    exporter.write(user)
```
