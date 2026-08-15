# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Released]

## [2.0.0] - 2026-08-15

### Removed

- **Breaking:** the Spring-style aliases `@service`, `@repository`,
  `@controller`, and `@adapter`. `@component` and `@provider` are now the only
  registration concepts; projects that want layer-specific names can alias
  `component` themselves (`service = component`).

## [Released]

## [1.0.0] - 2026-07-13

### Added

- `scan()` — the single entry point: recursively imports a package (or list of
  packages), filters registrations by active profile, and returns a `Container`.
  Also stores a process-wide container for `resolve()` / `get_container()`.
- `@component` decorator and the Spring-style aliases `@service`,
  `@repository`, `@controller`, and `@adapter`. Constructors are autowired —
  a plain type-annotated `__init__` needs no `@inject`.
- `@provider` decorator for custom factory functions, including conditional
  construction; the factory's own parameters are injected.
- `Scope` enum (`SINGLETON`, `TRANSIENT`, `THREAD`) mapping to `injector`'s
  singleton / noscope / threadlocal scopes. Accepts a raw `ScopeDecorator` too.
- Profile gating via `profiles=`, with `!name` negation.
- Named qualifiers: `bind=`/`provides=` with `name=`, resolved via
  `Container.get(T, name=...)` and `Container.get_all(T)`.
- Duplicate-binding detection with `DuplicateBindingError`; `ComponentNotFoundError`
  and `AmbiguousComponentError` for resolution failures.
