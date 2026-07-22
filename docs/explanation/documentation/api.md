---
audience: human, ai
status: stable
skills: [documentor]
---

# API Documentation Patterns

## Function Documentation

Every public function should document:

- **Purpose** — One sentence on what it does
- **Parameters** — Name, type, description, default value, whether required
- **Return value** — Type and description
- **Exceptions** — What errors it can raise and when
- **Example** — At least one usage example
- **Since** — Version when the function was introduced

## Class Documentation

- **Purpose** — What the class represents
- **Constructor parameters** — Same detail as function parameters
- **Public methods** — Each documented as a function
- **Properties** — Type and description
- **Usage example** — Instantiation through common operations

## Module Documentation

- **Overview** — What the module provides
- **Public API listing** — All exported classes, functions, constants
- **Dependency notes** — What this module requires
- **Usage patterns** — Common import and usage patterns

## API Doc Formats

| Format              | Best For              | Tooling                    |
| ------------------- | --------------------- | -------------------------- |
| Docstrings (Python) | Python libraries      | Sphinx, pdoc, mkdocstrings |
| JSDoc               | JavaScript/TypeScript | TypeDoc, documentation.js  |
| OpenAPI/Swagger     | REST APIs             | Swagger UI, Redoc          |
| GraphQL SDL         | GraphQL APIs          | GraphiQL, Apollo Studio    |
| gRPC Proto          | gRPC services         | protoc-gen-doc             |
