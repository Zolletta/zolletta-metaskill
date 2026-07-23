---
audience: human, ai
status: stable
skills: [patterns, review, python-*, php-*]
---
# Security (Language-Agnostic)

> Four rules adapted from [php-best-practices](https://skills.sh/php-community/php-best-practices) (MIT, v2.1.0). Examples in PHP and Python. The principles apply identically regardless of language.

## 1. Parameterized queries

Never concatenate user input into SQL. Use parameterized queries (prepared statements) to prevent SQL injection.

```php
// BAD: SQL injection
$sql = "SELECT * FROM users WHERE email = '" . $request->get('email') . "'";
$db->query($sql);

// GOOD: parameterized query
$sql = "SELECT * FROM users WHERE email = :email";
$db->query($sql, ['email' => $request->get('email')]);
```

```python
# BAD: SQL injection
sql = f"SELECT * FROM users WHERE email = '{request.args.get('email')}'"
db.execute(sql)

# GOOD: parameterized query
sql = "SELECT * FROM users WHERE email = %s"
db.execute(sql, (request.args.get("email"),))
```

## 2. Escape output

Never trust data before rendering it to the user. Escape it for the output context (HTML, URL, JavaScript, etc.).

```php
// BAD: XSS
echo "<h1>" . $user->getName() . "</h1>";

// GOOD: escape for HTML
echo "<h1>" . htmlspecialchars($user->getName(), ENT_QUOTES, 'UTF-8') . "</h1>";

// GOOD: use a templating engine that auto-escapes
// Twig: {{ user.name }}
// Blade: {{ $user->name }}
```

```python
# BAD: XSS
return f"<h1>{user.name}</h1>"

# GOOD: use a templating engine that auto-escapes
# Jinja2: {{ user.name }}
# Django: {{ user.name }}

# GOOD: manual escape
import html
return f"<h1>{html.escape(user.name)}</h1>"
```

## 3. Validate input

Validate all external input at the boundary (controller, API endpoint, CLI handler). Reject early with a clear error before the data reaches business logic.

```php
// BAD: no validation, trusts input
public function create(Request $request): Response {
    $user = new User($request->get('name'), $request->get('email'));
    $this->repo->save($user);
    return new Response(['id' => $user->getId()]);
}

// GOOD: validate at the boundary
public function create(Request $request): Response {
    $name = $request->get('name');
    $email = $request->get('email');

    if (empty($name) || strlen($name) > 255) {
        return new Response(['error' => 'Invalid name'], 400);
    }
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        return new Response(['error' => 'Invalid email'], 400);
    }

    $user = new User($name, $email);
    $this->repo->save($user);
    return new Response(['id' => $user->getId()]);
}
```

```python
# BAD: no validation, trusts input
def create(request: Request) -> Response:
    user = User(request.json["name"], request.json["email"])
    repo.save(user)
    return Response({"id": user.id})

# GOOD: validate at the boundary
def create(request: Request) -> Response:
    name = request.json.get("name", "")
    email = request.json.get("email", "")

    if not name or len(name) > 255:
        return Response({"error": "Invalid name"}, status=400)
    if "@" not in email or "." not in email.split("@")[-1]:
        return Response({"error": "Invalid email"}, status=400)

    user = User(name, email)
    repo.save(user)
    return Response({"id": user.id})
```

## 4. Store secrets in environment variables

Never hardcode secrets (API keys, database passwords, tokens) in source code. Read them from environment variables or a secrets manager.

```php
// BAD: hardcoded secret
$apiKey = 'sk_live_1234567890abcdef';
$client = new ApiClient($apiKey);

// GOOD: from environment
$apiKey = getenv('API_KEY') ?: throw new \RuntimeException('API_KEY not set');
$client = new ApiClient($apiKey);
```

```python
# BAD: hardcoded secret
api_key = "sk_live_1234567890abcdef"
client = ApiClient(api_key)

# GOOD: from environment
import os
api_key = os.environ["API_KEY"]  # raises KeyError if not set
client = ApiClient(api_key)
```
