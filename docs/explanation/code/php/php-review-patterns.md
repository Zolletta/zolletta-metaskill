---
audience: human, ai
status: stable
skills: [patterns, php-*]
---

# PHP Review Patterns

PHP-specific design patterns that go beyond the language-agnostic principles in [general-principles.md](../general-principles.md). Read this when reviewing PHP source code for structural quality.

> This file narrows down any eventual general rule about PHP. All files in `~/.agents/` are the single source of truth for their domain.

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

## SOLID Violation Patterns

The following SOLID violations are common in PHP codebases. Each pattern includes a before/after example and references the automated scanner that detects it. For scanner usage details, see [scripts.md](../../reference/code/scripts.md).

### Dependency Inversion Principle (DIP)

**Violation**: a class instantiates its dependencies with `new` in its constructor instead of receiving them via injection. The class is tightly coupled to a concrete implementation and cannot be substituted or tested in isolation.

**Before** — `new ConcreteClass()` in constructor:

```php
<?php

class OrderProcessor {
    private SmtpMailer $mailer;
    private FileLogger $logger;

    public function __construct() {
        $this->mailer = new SmtpMailer();       // tight coupling
        $this->logger = new FileLogger('/var/log/app.log');
    }

    public function process(Order $order): void {
        $this->mailer->send($order->getConfirmationEmail());
        $this->logger->log("Processed order {$order->getId()}");
    }
}
```

**After** — dependencies injected via constructor:

```php
<?php

class OrderProcessor {
    public function __construct(
        private MailerInterface $mailer,        // depends on abstraction
        private LoggerInterface $logger,
    ) {}

    public function process(Order $order): void {
        $this->mailer->send($order->getConfirmationEmail());
        $this->logger->log("Processed order {$order->getId()}");
    }
}
```

**Scanner**: [`scan_php_dependency_inversion`](../../reference/code/scripts.md#scan_php_dependency_inversionpy-dip) — detects `new ConcreteClass()` inside class methods. Excludes factories, builders, and PHP built-in types.

### Interface Segregation Principle (ISP)

**Violation**: a fat interface with many methods forces implementers to depend on methods they do not use. Implementers must provide stub or empty implementations for irrelevant methods.

**Before** — fat interface with too many methods:

```php
<?php

interface Worker {
    public function work(): void;
    public function eat(): void;
    public function sleep(): void;
    public function reportToManager(): void;
    public function submitTimesheet(): void;
    public function requestVacation(int $days): bool;
    public function attendMeeting(string $topic): void;
    public function writeReport(): string;
}

class Robot implements Worker {
    public function work(): void { /* ... */ }

    // Forced to implement irrelevant methods:
    public function eat(): void { /* robots don't eat */ }
    public function sleep(): void { /* robots don't sleep */ }
    public function reportToManager(): void { /* ... */ }
    public function submitTimesheet(): void { /* ... */ }
    public function requestVacation(int $days): bool { return false; }
    public function attendMeeting(string $topic): void { /* ... */ }
    public function writeReport(): string { return ''; }
}
```

**After** — split into focused interfaces:

```php
<?php

interface Workable {
    public function work(): void;
}

interface Reportable {
    public function writeReport(): string;
    public function reportToManager(): void;
}

interface Employable {
    public function submitTimesheet(): void;
    public function requestVacation(int $days): bool;
}

class Robot implements Workable, Reportable {
    public function work(): void { /* ... */ }
    public function writeReport(): string { /* ... */ }
    public function reportToManager(): void { /* ... */ }
}

class HumanWorker implements Workable, Reportable, Employable {
    public function work(): void { /* ... */ }
    public function writeReport(): string { /* ... */ }
    public function reportToManager(): void { /* ... */ }
    public function submitTimesheet(): void { /* ... */ }
    public function requestVacation(int $days): bool { /* ... */ }
}
```

**Scanner**: [`scan_php_interface_segregation`](../../reference/code/scripts.md#scan_php_interface_segregationpy-isp) — flags interfaces with more than `--min-methods` (default: 7) methods.

### Open/Closed Principle (OCP)

**Violation**: `instanceof` chains branch on subtypes. Adding a new subtype requires modifying the ladder instead of simply adding a new implementation.

**Before** — `instanceof` ladder:

```php
<?php

class PaymentProcessor {
    public function process(Payment $payment): void {
        if ($payment instanceof CreditCardPayment) {
            $this->processCreditCard($payment);
        } elseif ($payment instanceof PayPalPayment) {
            $this->processPayPal($payment);
        } elseif ($payment instanceof BankTransferPayment) {
            $this->processBankTransfer($payment);
        } elseif ($payment instanceof CryptoPayment) {
            // Adding a new payment type means modifying this method
            $this->processCrypto($payment);
        } else {
            throw new \InvalidArgumentException('Unknown payment type');
        }
    }
}
```

**After** — polymorphism via interface:

```php
<?php

interface PaymentStrategy {
    public function process(): void;
}

class CreditCardPayment implements PaymentStrategy {
    public function process(): void { /* credit card logic */ }
}

class PayPalPayment implements PaymentStrategy {
    public function process(): void { /* PayPal logic */ }
}

class BankTransferPayment implements PaymentStrategy {
    public function process(): void { /* bank transfer logic */ }
}

// Adding a new payment type = create a new class, no modification needed:
class CryptoPayment implements PaymentStrategy {
    public function process(): void { /* crypto logic */ }
}

class PaymentProcessor {
    public function process(PaymentStrategy $payment): void {
        $payment->process();  // closed for modification, open for extension
    }
}
```

**Scanner**: [`scan_php_open_closed`](../../reference/code/scripts.md#scan_php_open_closedpy-ocp) — detects `if/elseif` chains with 3+ `instanceof` branches.

## Manual Detection Commands

For PHP projects where AST-based scanners are not available (e.g. `tree-sitter-php` not installed), use grep for manual triage:

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
