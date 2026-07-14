"""Decorators that mark things for autowiring, and the registry they populate.

This module is the developer-facing surface of the library. Decorating a class
with :func:`component` (or a Spring-style alias such as :func:`service`) or a
factory function with :func:`provider` records a :class:`Registration` in a
:class:`Registry`. A later :func:`~injector_autowired.container.scan` imports the
modules so the decorators run, then turns the collected registrations into an
``injector`` container.

The module deliberately contains no scanning or container-construction logic, so
the decorators can be unit-tested in isolation and reused by any framework.

Autowiring note
---------------
Both decorators apply ``injector``'s :func:`~injector.inject` for you, so a
plain type-annotated ``__init__`` (or factory signature) has its dependencies
injected without any extra decorator — hence "autowired". A class that defines
no ``__init__`` of its own is left untouched, because ``inject`` cannot read
annotations off ``object.__init__``.
"""

from __future__ import annotations

import typing
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, overload

from injector import (
    CallableProvider,
    ClassProvider,
    Provider,
    ScopeDecorator,
    inject,
)

from .scopes import DEFAULT_SCOPE, ScopeLike, resolve_scope


@dataclass(frozen=True)
class Registration:
    """One thing to bind into the container.

    A registration comes from either a decorated class (``component`` set) or a
    decorated factory function (``factory`` set) — never both.
    """

    #: The interface/type callers resolve by. For a bare ``@component`` with no
    #: ``bind=`` this is the concrete class itself; for a provider it is the
    #: declared/inferred return type.
    interface: type
    #: Resolved ``injector`` scope controlling instance lifetime.
    scope: ScopeDecorator
    #: Qualifier used to tell apart several implementations of ``interface``.
    name: str | None
    #: Active-profile gate. Empty means "active in every profile".
    profiles: tuple[str, ...]
    #: The concrete class, when this registration came from ``@component``.
    component: type | None = None
    #: The factory function, when this registration came from ``@provider``.
    factory: Callable[..., Any] | None = None

    @property
    def is_qualified(self) -> bool:
        """Whether this registration carries a ``name=`` qualifier."""
        return self.name is not None

    def make_provider(self) -> Provider:
        """Build the ``injector`` provider that constructs the instance."""
        if self.factory is not None:
            return CallableProvider(self.factory)
        assert self.component is not None  # invariant: exactly one of the two
        return ClassProvider(self.component)

    def describe(self) -> str:
        """Human-readable identity, used in error messages."""
        target = self.component or self.factory
        qualifier = f" (name={self.name!r})" if self.name else ""
        return f"{getattr(target, '__qualname__', target)}{qualifier}"


class Registry:
    """An ordered, mutable collection of :class:`Registration` objects."""

    def __init__(self) -> None:
        self._registrations: list[Registration] = []

    def add(self, registration: Registration) -> None:
        self._registrations.append(registration)

    def all(self) -> list[Registration]:
        return list(self._registrations)

    def clear(self) -> None:
        self._registrations.clear()

    def __len__(self) -> int:
        return len(self._registrations)


#: The process-wide registry the decorators populate at import time.
registry = Registry()


def _auto_inject_class(cls: type) -> None:
    """Apply ``injector.inject`` to a class' own constructor, if it has one.

    Classes that only inherit ``object.__init__`` are skipped: ``inject`` would
    try to read annotations off the C-level slot wrapper and raise. Checking the
    MRO (rather than ``cls.__init__``) also covers a constructor inherited from a
    real base class.
    """
    defines_init = any(
        "__init__" in klass.__dict__ for klass in cls.__mro__ if klass is not object
    )
    if defines_init:
        inject(cls)


# --------------------------------------------------------------------------- #
# @component and its Spring-style aliases
# --------------------------------------------------------------------------- #


@overload
def component[C: type](cls: C, /) -> C: ...
@overload
def component[C: type](
    *,
    bind: type | None = ...,
    scope: ScopeLike = ...,
    name: str | None = ...,
    profiles: Sequence[str] = ...,
    into: Registry | None = ...,
) -> Callable[[C], C]: ...
def component[C: type](
    cls: C | None = None,
    /,
    *,
    bind: type | None = None,
    scope: ScopeLike = DEFAULT_SCOPE,
    name: str | None = None,
    profiles: Sequence[str] = (),
    into: Registry | None = None,
) -> C | Callable[[C], C]:
    """Register a class as an autowired component (singleton by default).

    Usable bare (``@component``) or parameterized (``@component(bind=Clock)``).
    The class' annotated ``__init__`` is wired automatically.

    Args:
        bind: an interface/ABC the class should also be resolvable as. When
            omitted, the class is resolvable only as itself.
        scope: a :class:`~injector_autowired.Scope` — ``Scope.SINGLETON``
            (default), ``Scope.TRANSIENT``, or ``Scope.THREAD`` — or a raw
            :class:`~injector.ScopeDecorator`.
        name: qualifier to disambiguate multiple implementations of ``bind``.
        profiles: profile gate; empty means active in every profile.
        into: target registry (defaults to the global one; handy in tests).
    """
    target_registry = registry if into is None else into
    resolved_scope = resolve_scope(scope)

    def wrap(decorated: C) -> C:
        _auto_inject_class(decorated)
        target_registry.add(
            Registration(
                interface=bind or decorated,
                scope=resolved_scope,
                name=name,
                profiles=tuple(profiles),
                component=decorated,
            )
        )
        return decorated

    return wrap(cls) if cls is not None else wrap


# Intent-revealing aliases (Spring-style): identical behavior, clearer at call sites.
service = component
repository = component
controller = component
adapter = component


# --------------------------------------------------------------------------- #
# @provider — custom factory functions
# --------------------------------------------------------------------------- #

_FactoryT = typing.TypeVar("_FactoryT", bound=Callable[..., Any])


def _infer_return_type(fn: Callable[..., Any]) -> type:
    """Read a factory's return annotation as the interface it provides."""
    try:
        hints = typing.get_type_hints(fn)
    except Exception as exc:  # unresolved forward ref, etc.
        raise TypeError(
            f"@provider {fn.__qualname__} has an unreadable return annotation; "
            f"pass provides= explicitly."
        ) from exc
    return_type = hints.get("return")
    if return_type is None:
        raise TypeError(
            f"@provider {fn.__qualname__} must annotate its return type or pass "
            f"provides= so the container knows what it builds."
        )
    return return_type


@overload
def provider(fn: _FactoryT, /) -> _FactoryT: ...
@overload
def provider(
    *,
    provides: type | None = ...,
    scope: ScopeLike = ...,
    name: str | None = ...,
    profiles: Sequence[str] = ...,
    into: Registry | None = ...,
) -> Callable[[_FactoryT], _FactoryT]: ...
def provider(
    fn: _FactoryT | None = None,
    /,
    *,
    provides: type | None = None,
    scope: ScopeLike = DEFAULT_SCOPE,
    name: str | None = None,
    profiles: Sequence[str] = (),
    into: Registry | None = None,
) -> _FactoryT | Callable[[_FactoryT], _FactoryT]:
    """Register a factory function that builds an instance itself.

    Use this when construction is conditional or needs logic the constructor
    can't express — the classic reason to reach for a custom provider. The
    factory's own annotated parameters are injected, so it can depend on other
    components. The interface it provides comes from the return annotation
    unless ``provides=`` is given.

    ::

        @provider(profiles=["prod"])
        def make_db(config: Config) -> Database:
            return PostgresDatabase(config.url)

    Args:
        provides: the interface to bind; defaults to the return annotation.
        scope: a :class:`~injector_autowired.Scope` — ``Scope.SINGLETON``
            (default), ``Scope.TRANSIENT``, or ``Scope.THREAD`` — or a raw
            :class:`~injector.ScopeDecorator`.
        name: qualifier to disambiguate multiple providers of the interface.
        profiles: profile gate; empty means active in every profile.
        into: target registry (defaults to the global one; handy in tests).
    """
    target_registry = registry if into is None else into
    resolved_scope = resolve_scope(scope)

    def wrap(decorated: _FactoryT) -> _FactoryT:
        interface = provides or _infer_return_type(decorated)
        inject(decorated)
        target_registry.add(
            Registration(
                interface=interface,
                scope=resolved_scope,
                name=name,
                profiles=tuple(profiles),
                factory=decorated,
            )
        )
        return decorated

    return wrap(fn) if fn is not None else wrap
