"""Package scanning: import modules so the decorators run.

This mirrors Spring Boot's component scan. Given one or more root packages,
every submodule beneath each is imported, which executes the ``@component`` and
``@provider`` decorators and populates the registry. Imports are idempotent
thanks to Python's module cache, so scanning the same package twice never
double-registers anything.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable, Sequence
from types import ModuleType


def import_packages(packages: str | Sequence[str]) -> None:
    """Import every module under each given package, recursively."""
    for package_name in _as_iterable(packages):
        module = importlib.import_module(package_name)
        _import_submodules(module)


def _as_iterable(packages: str | Sequence[str]) -> Iterable[str]:
    return [packages] if isinstance(packages, str) else packages


def _import_submodules(package: ModuleType) -> None:
    package_path = getattr(package, "__path__", None)
    if package_path is None:
        return  # a plain module, not a package — nothing to walk
    for module_info in pkgutil.walk_packages(package_path, prefix=f"{package.__name__}."):
        importlib.import_module(module_info.name)
