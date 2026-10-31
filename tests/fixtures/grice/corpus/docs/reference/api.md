# API Reference

Every template accepts the fields below, and a template that omits one gets the documented default.

## Fields

| Field      | Type    | Default |
|------------|---------|---------|
| `customer` | string  | none    |
| `total`    | decimal | `0.00`  |
| `currency` | string  | `EUR`   |

## Errors

An unknown field is reported by name, and the render stops before any file is written.
