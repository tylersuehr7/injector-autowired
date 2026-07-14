"""Profiles, named qualifiers, and duplicate detection."""

import pytest

from injector_autowired import (
    AmbiguousComponentError,
    ComponentNotFoundError,
    DuplicateBindingError,
    Registry,
    build,
    component,
    provider,
    service,
)


class Notifier:
    def send(self) -> str:
        raise NotImplementedError


def _two_notifiers(reg: Registry) -> None:
    @service(bind=Notifier, profiles=["prod"], into=reg)
    class EmailNotifier(Notifier):
        def send(self) -> str:
            return "email"

    @service(bind=Notifier, profiles=["test"], into=reg)
    class NullNotifier(Notifier):
        def send(self) -> str:
            return "noop"


def test_profile_selects_the_active_implementation():
    reg = Registry()
    _two_notifiers(reg)

    prod = build(reg.all(), profiles=["prod"])
    assert prod.get(Notifier).send() == "email"

    test = build(reg.all(), profiles=["test"])
    assert test.get(Notifier).send() == "noop"


def test_unprofiled_component_is_always_active():
    reg = Registry()

    @component(into=reg)
    class Always:
        pass

    assert isinstance(build(reg.all(), profiles=["anything"]).get(Always), Always)


def test_negated_profile():
    reg = Registry()

    @service(bind=Notifier, profiles=["!test"], into=reg)
    class RealNotifier(Notifier):
        def send(self) -> str:
            return "real"

    assert build(reg.all(), profiles=["prod"]).get(Notifier).send() == "real"
    with pytest.raises(ComponentNotFoundError):
        build(reg.all(), profiles=["test"]).get(Notifier)


def test_conditional_provider_by_profile():
    reg = Registry()

    class Cache:
        def kind(self) -> str:
            raise NotImplementedError

    @provider(profiles=["prod"], into=reg)
    def redis_cache() -> Cache:
        c = Cache()
        c.kind = lambda: "redis"  # type: ignore[method-assign]
        return c

    @provider(profiles=["dev"], into=reg)
    def memory_cache() -> Cache:
        c = Cache()
        c.kind = lambda: "memory"  # type: ignore[method-assign]
        return c

    assert build(reg.all(), profiles=["prod"]).get(Cache).kind() == "redis"
    assert build(reg.all(), profiles=["dev"]).get(Cache).kind() == "memory"


def test_two_active_unqualified_implementations_raise():
    reg = Registry()

    @service(bind=Notifier, into=reg)
    class A(Notifier):
        def send(self) -> str:
            return "a"

    @service(bind=Notifier, into=reg)
    class B(Notifier):
        def send(self) -> str:
            return "b"

    with pytest.raises(DuplicateBindingError, match="Notifier"):
        build(reg.all())


def test_two_implementations_with_the_same_name_raise():
    reg = Registry()

    @service(bind=Notifier, name="primary", into=reg)
    class A(Notifier):
        def send(self) -> str:
            return "a"

    @service(bind=Notifier, name="primary", into=reg)
    class B(Notifier):
        def send(self) -> str:
            return "b"

    with pytest.raises(DuplicateBindingError, match="Notifier"):
        build(reg.all())


def test_named_qualifiers_disambiguate():
    reg = Registry()

    @service(bind=Notifier, name="email", into=reg)
    class EmailNotifier(Notifier):
        def send(self) -> str:
            return "email"

    @service(bind=Notifier, name="sms", into=reg)
    class SmsNotifier(Notifier):
        def send(self) -> str:
            return "sms"

    container = build(reg.all())
    assert container.get(Notifier, name="email").send() == "email"
    assert container.get(Notifier, name="sms").send() == "sms"


def test_unnamed_resolve_with_only_named_is_ambiguous():
    reg = Registry()

    @service(bind=Notifier, name="email", into=reg)
    class EmailNotifier(Notifier):
        def send(self) -> str:
            return "email"

    @service(bind=Notifier, name="sms", into=reg)
    class SmsNotifier(Notifier):
        def send(self) -> str:
            return "sms"

    with pytest.raises(AmbiguousComponentError):
        build(reg.all()).get(Notifier)


def test_missing_named_component_raises():
    reg = Registry()

    @service(bind=Notifier, name="email", into=reg)
    class EmailNotifier(Notifier):
        def send(self) -> str:
            return "email"

    with pytest.raises(ComponentNotFoundError, match="nope"):
        build(reg.all()).get(Notifier, name="nope")


def test_get_all_returns_every_implementation():
    reg = Registry()

    @service(bind=Notifier, name="email", into=reg)
    class EmailNotifier(Notifier):
        def send(self) -> str:
            return "email"

    @service(bind=Notifier, name="sms", into=reg)
    class SmsNotifier(Notifier):
        def send(self) -> str:
            return "sms"

    everyone = build(reg.all()).get_all(Notifier)
    assert {k: v.send() for k, v in everyone.items()} == {
        "email": "email",
        "sms": "sms",
    }


def test_named_and_unnamed_coexist():
    reg = Registry()

    @service(bind=Notifier, into=reg)
    class Default(Notifier):
        def send(self) -> str:
            return "default"

    @service(bind=Notifier, name="sms", into=reg)
    class SmsNotifier(Notifier):
        def send(self) -> str:
            return "sms"

    container = build(reg.all())
    assert container.get(Notifier).send() == "default"
    assert container.get(Notifier, name="sms").send() == "sms"
