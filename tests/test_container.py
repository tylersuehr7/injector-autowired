"""Container construction details and the ``scan`` entry point's options."""

import pytest
from injector import Injector

from injector_autowired import (
    Container,
    DuplicateBindingError,
    Registry,
    build,
    component,
    provider,
    scan,
)


class Clock:
    def now(self) -> str:
        raise NotImplementedError


def test_injector_property_exposes_the_native_container():
    reg = Registry()

    @component(into=reg)
    class Widget:
        pass

    container = build(reg.all())
    assert isinstance(container.injector, Injector)
    # The native injector resolves the same instances.
    assert container.injector.get(Widget) is container.get(Widget)


def test_component_and_provider_claiming_one_interface_collide():
    reg = Registry()

    @component(bind=Clock, into=reg)
    class SystemClock(Clock):
        def now(self) -> str:
            return "tick"

    @provider(provides=Clock, into=reg)
    def make_clock() -> Clock:
        return SystemClock()

    with pytest.raises(DuplicateBindingError, match="Clock"):
        build(reg.all())


def test_get_all_keys_unnamed_by_class_name():
    reg = Registry()

    @component(bind=Clock, into=reg)
    class SystemClock(Clock):
        def now(self) -> str:
            return "tick"

    everyone = build(reg.all()).get_all(Clock)
    assert list(everyone) == ["SystemClock"]
    assert everyone["SystemClock"].now() == "tick"


def test_scan_without_packages_uses_the_given_registry():
    reg = Registry()

    @component(into=reg)
    class AlreadyImported:
        pass

    # No packages to import; scan just filters and builds from `source`.
    container = scan(profiles=[], source=reg, set_global=False)
    assert isinstance(container, Container)
    assert isinstance(container.get(AlreadyImported), AlreadyImported)


def test_scan_set_global_false_leaves_global_untouched():
    import injector_autowired.container as container_module

    container_module._current = None
    reg = Registry()

    @component(into=reg)
    class Thing:
        pass

    scan(source=reg, set_global=False)
    assert container_module._current is None
