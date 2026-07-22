---
audience: human, ai
status: stable
skills: [patterns]
---

# PHP Review Patterns

PHP-specific design patterns that go beyond the language-agnostic principles in [general-principles.md](../general-principles.md). Read this when reviewing PHP source code for structural quality.

## Strategy Pattern with Autodiscovery

PHP does not have a built-in equivalent of Python's `Protocol` + decorator registration, but the strategy pattern can be implemented using interfaces and registration arrays or attribute-based discovery.

### Interface + array registration

```php
<?php

interface ScenarioStrategy {
    public function generate(Spec $spec): array;
    public function getName(): string;
}

// Registry pattern — strategies register themselves or are registered centrally
class StrategyRegistry {
    /** @var array<string, class-string<ScenarioStrategy>> */
    private static array $strategies = [];

    public static function register(string $name, string $class): void {
        self::$strategies[$name] = $class;
    }

    public static function get(string $name): ScenarioStrategy {
        $class = self::$strategies[$name];
        return new $class();
    }

    /** @return array<string, class-string<ScenarioStrategy>> */
    public static function all(): array {
        return self::$strategies;
    }
}

StrategyRegistry::register('feature_flag', FeatureFlagStrategy::class);
StrategyRegistry::register('pipeline_type', PipelineTypeStrategy::class);
```

### Attribute-based registration (PHP 8.0+)

```php
<?php

#[\Attribute(\Attribute::TARGET_CLASS)]
class RegisterStrategy {
    public function __construct(public readonly string $name) {}
}

#[RegisterStrategy('feature_flag')]
class FeatureFlagStrategy implements ScenarioStrategy {
    public function generate(Spec $spec): array { /* ... */ }
    public function getName(): string { return 'feature_flag'; }
}

// Discovery via reflection
class StrategyDiscovery {
    /** @return array<string, class-string<ScenarioStrategy>> */
    public static function discover(string $directory): array {
        $strategies = [];
        // Scan directory for PHP files, use reflection to find
        // classes with #[RegisterStrategy] attribute
        // ...
        return $strategies;
    }
}
```

**Why this matters**: this is the OCP-compliant alternative to if/elseif type branching. Adding a new strategy requires zero modification to existing dispatch logic — just create a new class and register it.

## Interface vs Abstract Class

PHP offers both interfaces and abstract classes for defining contracts. Choose the right one:

- **Interface** (`interface`): use for pure contracts — a set of method signatures that implementers must provide. A class can implement multiple interfaces. No implementation is shared.
- **Abstract class** (`abstract class`): use when you want to share implementation across related classes. A class can only extend one abstract class. Can mix abstract methods (must be implemented) with concrete methods (shared implementation).

**Prefer interfaces** for defining contracts that multiple unrelated classes can satisfy. Use abstract classes when there is genuine shared implementation that would otherwise be duplicated.

```php
<?php

// Interface: pure contract — any class can implement it
interface Cacheable {
    public function getCacheKey(): string;
    public function getTtl(): int;
}

// Abstract class: shared implementation + contract
abstract class BaseRepository {
    public function __construct(protected Database $db) {}

    // Shared implementation — subclasses don't reimplement this
    public function findById(int $id): ?array {
        return $this->db->fetchOne(
            "SELECT * FROM {$this->getTableName()} WHERE id = ?",
            [$id]
        );
    }

    // Contract — subclasses must implement this
    abstract protected function getTableName(): string;
}
```

**ISP reminder**: keep interfaces thin. If an interface has 5+ methods and different implementers only use subsets, split it into smaller, focused interfaces. See [general-principles.md](../general-principles.md) → Interface Segregation.

## Trait Patterns

PHP traits provide horizontal code reuse — a way to share methods across classes without inheritance. Use traits for small, focused pieces of shared behavior.

**Guidelines**:

- Keep traits small and focused (one responsibility per trait).
- Traits should not define state (properties) unless absolutely necessary — prefer constructor injection.
- A trait should be composable: a class should be able to use the trait without requiring other traits or specific class structure.
- Name traits after the behavior they provide, not the class they serve (`SoftDeletes` not `UserTrait`).

```php
<?php

// Good: small, focused, no state
trait Timestampable {
    public function touch(): void {
        $this->updatedAt = new \DateTimeImmutable();
    }

    public function isStale(int $thresholdSeconds): bool {
        $age = time() - $this->updatedAt->getTimestamp();
        return $age > $thresholdSeconds;
    }
}

// Avoid: trait with too many responsibilities
trait BadTrait {
    public function log() { /* ... */ }
    public function cache() { /* ... */ }
    public function validate() { /* ... */ }
    public function serialize() { /* ... */ }
    // This is a God trait — split it into focused traits
}
```

## Manual Detection Commands

For PHP projects where AST-based scanners are not available, use grep for manual triage:

```bash
# Find if/elseif chains with instanceof or get_class (OCP violation signal)
grep -rn "instanceof\|get_class(" src/ --include="*.php" | head -20

# Find internal dependency creation in class constructors (DIP violation signal)
grep -rn "new \|->.* = new " src/ --include="*.php" | grep -v "Factory\|Builder"

# Find large classes (triage signal for God class detection)
find src/ -name "*.php" -exec wc -l {} + | sort -rn | head -20

# Find classes with many public methods (triage signal)
grep -rn "public function" src/ --include="*.php" | cut -d: -f1 | sort | uniq -c | sort -rn | head -20
```

These commands produce triage signals, not verdicts. Always apply the "reason to change" test before reporting a class as a God class. See [false-positive-prevention.md](../false-positive-prevention.md) for the mandatory judgment steps.
