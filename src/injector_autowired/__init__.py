"""Spring-Boot-style autowiring for the Python ``injector`` library.

Mark classes and factories with decorators, then call :func:`scan` once at
startup — no manual modules or bindings::

    # billing/services.py
    from injector_autowired import component, provider, inject

    @component(bind=Clock)
    class SystemClock(Clock): ...

    @component
    class InvoiceService:
        @inject
        def __init__(self, clock: Clock): ...

    @provider(profiles=["prod"])
    def make_db(config: Config) -> Database:
        return PostgresDatabase(config.url)

    # app startup
    from injector_autowired import scan
    container = scan("billing", profiles=["prod"])
    invoices = container.get(InvoiceService)

Scopes are named: ``"singleton"`` (default), ``"transient"`` (new every time),
and ``"thread"`` (one per thread).
"""

from __future__ import annotations

from injector import inject, noscope, singleton, threadlocal

from .container import (
    Container,
    build,
    get_container,
    resolve,
    scan,
)
from .errors import (
    AmbiguousComponentError,
    AutowireError,
    ComponentNotFoundError,
    DuplicateBindingError,
)
from .registry import (
    Registration,
    Registry,
    component,
    provider,
    registry,
)
from .scopes import Scope, resolve_scope

__all__ = [
    # entry points
    "scan",
    "build",
    "resolve",
    "get_container",
    "Container",
    # decorators
    "component",
    "provider",
    # registry
    "Registration",
    "Registry",
    "registry",
    # scopes / injector re-exports
    "Scope",
    "resolve_scope",
    "inject",
    "singleton",
    "noscope",
    "threadlocal",
    # errors
    "AutowireError",
    "DuplicateBindingError",
    "ComponentNotFoundError",
    "AmbiguousComponentError",
]
