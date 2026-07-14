"""Turn scanned registrations into an ``injector`` container and query it.

Responsibilities are split cleanly:

* ``injector`` owns construction, ``@inject`` wiring, and scope lifetimes. Every
  active registration is bound there under a stable *key*.
* :class:`Container` owns the qualifier logic Spring gives you — resolving an
  interface to one of several named implementations — by consulting the
  registrations it was built from.

:func:`scan` is the single public entry point: import packages, filter by
profile, build the container. Any framework can call it once at startup (e.g.
Django from ``AppConfig.ready``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from injector import Binder, Injector, Module, Provider

from .errors import (
    AmbiguousComponentError,
    ComponentNotFoundError,
    DuplicateBindingError,
)
from .registry import Registration, Registry
from .registry import registry as default_registry
from .scanner import import_packages


@dataclass(frozen=True)
class _BindingPlan:
    """A registration paired with the ``injector`` key it is bound under."""

    registration: Registration
    key: type
    provider: Provider


def _profile_active(registration: Registration, active: tuple[str, ...]) -> bool:
    """Whether a registration is active given the set of active profiles.

    A registration with no profiles is always active. Otherwise it is active if
    *any* of its profiles matches: a plain name must be present in ``active``; a
    ``"!name"`` entry matches when ``name`` is absent.
    """
    if not registration.profiles:
        return True
    for profile in registration.profiles:
        if profile.startswith("!"):
            if profile[1:] not in active:
                return True
        elif profile in active:
            return True
    return False


def _binding_key(registration: Registration) -> type:
    """The type a registration is bound under inside ``injector``.

    Unqualified registrations are bound under the interface they provide, so
    injection-by-type works. Qualified ones need a unique key: a component uses
    its concrete class, and a provider gets a synthetic marker type (its factory
    has no distinct class of its own).
    """
    if registration.name is None:
        return registration.interface
    if registration.component is not None:
        return registration.component
    return type(
        f"_Qualified_{registration.interface.__name__}_{registration.name}",
        (),
        {},
    )


def _plan_bindings(registrations: Sequence[Registration]) -> list[_BindingPlan]:
    """Assign a binding key to each registration and reject duplicate claims.

    Two registrations conflict when they would resolve to the same thing: an
    unqualified pair claiming one interface, or a qualified pair sharing the same
    ``(interface, name)``.
    """
    plans: list[_BindingPlan] = []
    claimed: dict[object, Registration] = {}
    for registration in registrations:
        # The identity two registrations must not share.
        claim: object = (
            (registration.interface, registration.name)
            if registration.name is not None
            else registration.interface
        )
        if claim in claimed:
            other = claimed[claim]
            raise DuplicateBindingError(
                f"{registration.interface.__name__} is claimed by both "
                f"{other.describe()} and {registration.describe()}; give one a "
                f"different name= qualifier or gate them behind different profiles."
            )
        claimed[claim] = registration
        key = _binding_key(registration)
        plans.append(_BindingPlan(registration, key, registration.make_provider()))
    return plans


class _AutowireModule(Module):
    """Binds each planned registration into ``injector``."""

    def __init__(self, plans: Sequence[_BindingPlan]) -> None:
        self._plans = plans

    def configure(self, binder: Binder) -> None:
        for plan in self._plans:
            binder.bind(plan.key, to=plan.provider, scope=plan.registration.scope)


class Container:
    """Resolves components, including interface-to-implementation qualifiers."""

    def __init__(self, injector: Injector, plans: Sequence[_BindingPlan]) -> None:
        self._injector = injector
        self._plans = list(plans)

    @property
    def injector(self) -> Injector:
        """The underlying ``injector.Injector`` for advanced use."""
        return self._injector

    def get[T](self, interface: type[T], *, name: str | None = None) -> T:
        """Resolve an instance for ``interface`` (optionally a named one).

        Args:
            interface: the type to resolve.
            name: qualifier selecting a specific named implementation.

        Raises:
            ComponentNotFoundError: no registration matches.
            AmbiguousComponentError: only named implementations exist and no
                ``name`` was given.
        """
        if name is not None:
            for plan in self._plans:
                if plan.registration.interface is interface and plan.registration.name == name:
                    return self._injector.get(plan.key)
            raise ComponentNotFoundError(
                f"No component named {name!r} provides {interface.__name__}."
            )

        matches = [p for p in self._plans if p.registration.interface is interface]
        if not matches:
            raise ComponentNotFoundError(
                f"No active component provides {interface.__name__}. Check that it "
                f"is decorated, that its module was scanned, and that its profile "
                f"is active."
            )
        unqualified = [p for p in matches if p.registration.name is None]
        if len(unqualified) == 1:
            return self._injector.get(unqualified[0].key)
        raise AmbiguousComponentError(
            f"{interface.__name__} has only named implementations "
            f"({', '.join(p.registration.name or '?' for p in matches)}); "
            f"resolve with name= or get_all()."
        )

    def get_all[T](self, interface: type[T]) -> dict[str, T]:
        """Resolve every implementation of ``interface``, keyed by qualifier.

        Unqualified implementations are keyed by their class name.
        """
        result: dict[str, T] = {}
        for plan in self._plans:
            reg = plan.registration
            if reg.interface is interface:
                target = reg.component or reg.factory
                key: str = reg.name or getattr(target, "__name__", None) or repr(target)
                result[key] = self._injector.get(plan.key)
        return result


def build(
    registrations: Sequence[Registration],
    *,
    profiles: Sequence[str] = (),
) -> Container:
    """Filter registrations by profile and build a :class:`Container`.

    Lower-level than :func:`scan`: it takes registrations directly instead of
    scanning packages, which makes it convenient for tests.
    """
    active_profiles = tuple(profiles)
    active = [r for r in registrations if _profile_active(r, active_profiles)]
    plans = _plan_bindings(active)
    injector = Injector([_AutowireModule(plans)])
    return Container(injector, plans)


_current: Container | None = None


def scan(
    packages: str | Sequence[str] | None = None,
    *,
    profiles: Sequence[str] = (),
    source: Registry | None = None,
    set_global: bool = True,
) -> Container:
    """Scan packages, filter by profile, and build the container.

    This is the single entry point. Call it once after your application is
    ready (for example, a Django ``AppConfig.ready`` hook).

    Args:
        packages: a package name or list of names to import recursively. When
            ``None``, nothing is imported and the current registry is used as-is
            (useful when modules are already imported).
        profiles: the set of active profiles. A registration with ``profiles=``
            is included only when one of them is active.
        source: registry to read registrations from (defaults to the global
            one populated by the decorators).
        set_global: also store the result as the process-wide container so
            :func:`resolve` and :func:`get_container` work.

    Returns:
        A :class:`Container` wrapping the built ``injector`` container.
    """
    if packages is not None:
        import_packages(packages)
    reg = source or default_registry
    container = build(reg.all(), profiles=profiles)
    if set_global:
        global _current
        _current = container
    return container


def get_container() -> Container:
    """Return the process-wide container, or raise if :func:`scan` hasn't run."""
    if _current is None:
        raise RuntimeError("Container not built yet; call scan() first.")
    return _current


def resolve[T](interface: type[T], *, name: str | None = None) -> T:
    """Resolve from the process-wide container built by :func:`scan`."""
    return get_container().get(interface, name=name)
