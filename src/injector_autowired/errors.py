"""Exceptions raised while building or querying a container."""

from __future__ import annotations


class AutowireError(Exception):
    """Base class for every error this library raises."""


class DuplicateBindingError(AutowireError):
    """Two active registrations claim the same, unqualified interface.

    Resolve it by giving one component a ``name=`` qualifier, or by gating the
    alternatives behind different ``profiles=``.
    """


class ComponentNotFoundError(AutowireError):
    """No registered component matches the requested interface (and name)."""


class AmbiguousComponentError(AutowireError):
    """Several named components match; the caller must supply a ``name=``."""
