"""Component registration, wiring, and scope behavior."""

import threading

import pytest
from injector import ScopeDecorator, SingletonScope

from injector_autowired import (
    Registry,
    Scope,
    build,
    component,
    controller,
    inject,
    repository,
    service,
)


def test_bare_component_resolvable_as_itself():
    reg = Registry()

    @component(into=reg)
    class Widget:
        pass

    container = build(reg.all())
    assert isinstance(container.get(Widget), Widget)


def test_constructor_is_autowired_without_explicit_inject():
    reg = Registry()

    @component(into=reg)
    class Engine:
        pass

    @component(into=reg)
    class Car:
        def __init__(self, engine: Engine):  # no @inject needed
            self.engine = engine

    container = build(reg.all())
    assert isinstance(container.get(Car).engine, Engine)


def test_bind_makes_class_resolvable_as_interface():
    reg = Registry()

    class Clock:
        def now(self) -> str:
            raise NotImplementedError

    @service(bind=Clock, into=reg)
    class SystemClock(Clock):
        def now(self) -> str:
            return "tick"

    container = build(reg.all())
    assert container.get(Clock).now() == "tick"
    assert isinstance(container.get(Clock), SystemClock)


def test_interface_is_injected_into_dependents():
    reg = Registry()

    class Repo:
        pass

    @repository(bind=Repo, into=reg)
    class SqlRepo(Repo):
        pass

    @service(into=reg)
    class UseCase:
        @inject
        def __init__(self, repo: Repo):
            self.repo = repo

    container = build(reg.all())
    assert isinstance(container.get(UseCase).repo, SqlRepo)


def test_singleton_is_the_default_scope():
    reg = Registry()

    @component(into=reg)
    class Cache:
        pass

    container = build(reg.all())
    assert container.get(Cache) is container.get(Cache)


def test_transient_scope_yields_new_instances():
    reg = Registry()

    @component(scope=Scope.TRANSIENT, into=reg)
    class Request:
        pass

    container = build(reg.all())
    assert container.get(Request) is not container.get(Request)


def test_thread_scope_is_per_thread():
    reg = Registry()

    @component(scope=Scope.THREAD, into=reg)
    class ThreadState:
        pass

    container = build(reg.all())
    main_instance = container.get(ThreadState)
    assert container.get(ThreadState) is main_instance

    other: dict[str, object] = {}

    def worker():
        other["value"] = container.get(ThreadState)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert other["value"] is not main_instance


def test_string_scope_still_coerces_to_the_enum():
    # Scope is a StrEnum, so the plain value keeps working for convenience.
    reg = Registry()

    @component(scope="transient", into=reg)
    class Request:
        pass

    container = build(reg.all())
    assert container.get(Request) is not container.get(Request)


def test_raw_scope_decorator_is_accepted():
    reg = Registry()

    @component(scope=ScopeDecorator(SingletonScope), into=reg)
    class Cache:
        pass

    container = build(reg.all())
    assert container.get(Cache) is container.get(Cache)


def test_unknown_scope_is_rejected_at_decoration():
    with pytest.raises(ValueError, match="Unknown scope"):

        @component(scope="request")  # not a real scope
        class Bad:
            pass


def test_aliases_behave_like_component():
    reg = Registry()

    @service(into=reg)
    class A:
        pass

    @repository(into=reg)
    class B:
        pass

    @controller(into=reg)
    class C:
        pass

    container = build(reg.all())
    assert isinstance(container.get(A), A)
    assert isinstance(container.get(B), B)
    assert isinstance(container.get(C), C)
