"""Memory scopes and their translation to ``injector`` scopes.

The library speaks in a small :class:`Scope` enum — ``Scope.SINGLETON``,
``Scope.TRANSIENT`` and ``Scope.THREAD`` — so component authors never import
``injector`` internals just to say how long an instance should live. Each member
maps to the ``injector`` :class:`~injector.ScopeDecorator` that implements it:

=================  ===========================  ==================================
Member             ``injector`` scope           Lifetime
=================  ===========================  ==================================
``SINGLETON``      :data:`~injector.singleton`     One instance per container (default).
``TRANSIENT``      :data:`~injector.noscope`       A fresh instance on every resolve.
``THREAD``         :data:`~injector.threadlocal`   One instance per thread.
=================  ===========================  ==================================

:class:`Scope` is a :class:`~enum.StrEnum`, so ``Scope.SINGLETON == "singleton"``
and the plain strings still coerce cleanly — but the enum is the canonical,
type-checked way to name a scope. A raw :class:`~injector.ScopeDecorator` is also
accepted anywhere a scope is, so power users can supply a custom scope.
"""

from __future__ import annotations

from enum import StrEnum

from injector import ScopeDecorator, noscope, singleton, threadlocal


class Scope(StrEnum):
    """The instance-lifetime scopes a component or provider may declare."""

    #: One instance per container (the default).
    SINGLETON = "singleton"
    #: A fresh instance every time the type is resolved.
    TRANSIENT = "transient"
    #: One instance per thread.
    THREAD = "thread"


#: The scope used when a component or provider does not specify one.
DEFAULT_SCOPE = Scope.SINGLETON

_SCOPES: dict[Scope, ScopeDecorator] = {
    Scope.SINGLETON: singleton,
    Scope.TRANSIENT: noscope,
    Scope.THREAD: threadlocal,
}

#: What callers may pass as a scope: a :class:`Scope` member or a raw decorator.
ScopeLike = Scope | ScopeDecorator


def resolve_scope(scope: ScopeLike | str) -> ScopeDecorator:
    """Translate a :class:`Scope` (or pass through a :class:`ScopeDecorator`).

    Args:
        scope: a :class:`Scope` member, its string value, or a ready-made
            :class:`~injector.ScopeDecorator`.

    Raises:
        ValueError: if ``scope`` is not a recognized :class:`Scope`.
    """
    if isinstance(scope, ScopeDecorator):
        return scope
    try:
        member = Scope(scope)
    except ValueError:
        valid = ", ".join(f"Scope.{s.name}" for s in Scope)
        raise ValueError(
            f"Unknown scope {scope!r}; expected one of {valid} or a ScopeDecorator."
        ) from None
    return _SCOPES[member]
