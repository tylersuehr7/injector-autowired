# injector-autowired

> Spring-Boot-style autowiring for the Python [`injector`](https://github.com/python-injector/injector) library. Zero manual wiring.

[![PyPI version](https://img.shields.io/pypi/v/injector-autowired.svg)](https://pypi.org/project/injector-autowired/)
[![Python versions](https://img.shields.io/pypi/pyversions/injector-autowired.svg)](https://pypi.org/project/injector-autowired/)
[![License](https://img.shields.io/pypi/l/injector-autowired.svg)](https://github.com/tylersuehr7/injector-autowired/blob/main/LICENSE)
[![CI](https://github.com/tylersuehr7/injector-autowired/actions/workflows/ci.yml/badge.svg)](https://github.com/tylersuehr7/injector-autowired/actions/workflows/ci.yml)

Decorate your classes and factories, point a single `scan()` call at your
package, and get a fully wired container back. No hand-written `Module`
subclasses, no `binder.bind(...)` calls.

```python
from injector_autowired import service, provider, scan, inject

class Clock:
    def now(self) -> str: ...

@service(bind=Clock)
class SystemClock(Clock):
    def now(self) -> str:
        return "2026-07-12T00:00:00Z"

@service
class InvoiceService:
    def __init__(self, clock: Clock):     # autowired — no @inject needed
        self.clock = clock

@provider(profiles=["prod"])
def make_database(config: Config) -> Database:
    return PostgresDatabase(config.url)   # conditional construction

# once, at startup:
container = scan("billing", profiles=["prod"])
invoices = container.get(InvoiceService)
```

## Install

```bash
pip install injector-autowired   # depends on `injector`
```

## The one entry point: `scan`

```python
container = scan("myapp", profiles=["prod"])
```

`scan(packages, *, profiles=(), source=None, set_global=True)` imports every
module under each package (recursively) so the decorators run, filters
registrations by active profile, and returns a `Container`. It also stores the
result as a process-wide container, so `resolve(SomeType)` works anywhere.

Any framework can call it once its app is ready — for example, Django from
`AppConfig.ready`:

```python
class BillingConfig(AppConfig):
    def ready(self):
        from injector_autowired import scan
        scan("billing", profiles=settings.ACTIVE_PROFILES)
```

Resolve things with `container.get(T)`, or globally with `resolve(T)`.

## Decorators

| Decorator | Marks | Notes |
|-----------|-------|-------|
| `@component` | a class | Base marker. `@service`, `@repository`, `@controller`, `@adapter` are identical aliases that read better at call sites. |
| `@provider` | a factory function | Builds the instance itself; use for conditional or logic-heavy construction. The interface comes from the return annotation (or `provides=`). |

Both wire dependencies automatically: a plain type-annotated `__init__` (or
factory signature) has its parameters injected for you.

### Binding an interface

```python
@service(bind=Clock)
class SystemClock(Clock): ...
```

`bind=` makes the class resolvable as the interface, so anything depending on
`Clock` gets `SystemClock`.

## Scopes

Scopes are a `Scope` enum; they control instance lifetime:

| Member | Lifetime |
|--------|----------|
| `Scope.SINGLETON` (default) | One instance per container. |
| `Scope.TRANSIENT` | A fresh instance on every resolve. |
| `Scope.THREAD` | One instance per thread. |

```python
from injector_autowired import Scope, component

@component(scope=Scope.TRANSIENT)
class RequestContext: ...
```

`Scope` is a `StrEnum`, so the plain strings (`"transient"`, …) still work, and
a raw `injector.ScopeDecorator` is accepted for custom scopes.

## Profiles

Gate a registration to certain environments. A registration with no profiles is
always active; otherwise it is active when **any** of its profiles matches.
Prefix with `!` to mean "active unless this profile is on".

```python
@service(bind=Notifier, profiles=["prod"])
class EmailNotifier(Notifier): ...

@service(bind=Notifier, profiles=["!prod"])
class ConsoleNotifier(Notifier): ...

scan("myapp", profiles=["prod"]).get(Notifier)   # -> EmailNotifier
```

## Custom providers

When construction is conditional or needs logic a constructor can't express,
use a factory. Its parameters are injected like any component's:

```python
@provider(scope=Scope.SINGLETON, profiles=["prod"])
def make_cache(settings: Settings) -> Cache:
    return RedisCache(settings.redis_url)
```

## Multiple implementations (qualifiers)

Register several implementations of one interface with `name=`, then resolve by
name — or fetch them all:

```python
@adapter(bind=BookingProvider, name="fareharbor")
class FareHarborProvider(BookingProvider): ...

@adapter(bind=BookingProvider, name="peek")
class PeekProvider(BookingProvider): ...

container.get(BookingProvider, name="peek")   # one of them
container.get_all(BookingProvider)            # {"fareharbor": ..., "peek": ...}
```

Two *unqualified* components claiming the same interface is an error
(`DuplicateBindingError`) — give one a `name=` or gate them behind profiles.

## Errors

- `DuplicateBindingError` — two active, unqualified registrations claim one interface.
- `ComponentNotFoundError` — nothing (active) provides the requested interface/name.
- `AmbiguousComponentError` — only named implementations exist and no `name=` was given.

All inherit from `AutowireError`.

## License

MIT © 2026 Tyler R. Suehr
