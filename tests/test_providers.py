"""Custom provider factories."""

import pytest

from injector_autowired import Registry, Scope, build, component, provider


class Config:
    def __init__(self) -> None:
        self.url = "sqlite://"


class Database:
    def __init__(self, url: str) -> None:
        self.url = url


def test_provider_binds_its_return_type():
    reg = Registry()

    @provider(into=reg)
    def make_config() -> Config:
        config = Config()
        config.url = "postgres://prod"
        return config

    container = build(reg.all())
    assert container.get(Config).url == "postgres://prod"


def test_provider_receives_injected_dependencies():
    reg = Registry()

    @component(into=reg)
    class Config2(Config):
        pass

    @provider(provides=Database, into=reg)
    def make_db(config: Config2) -> Database:
        return Database(config.url)

    container = build(reg.all())
    assert container.get(Database).url == "sqlite://"


def test_provides_overrides_return_annotation():
    reg = Registry()

    class Animal:
        pass

    class Dog(Animal):
        pass

    @provider(provides=Animal, into=reg)
    def make_animal() -> Dog:
        return Dog()

    container = build(reg.all())
    assert isinstance(container.get(Animal), Dog)


def test_provider_singleton_by_default_and_transient_on_request():
    reg = Registry()

    @provider(into=reg)
    def make_default() -> Config:
        return Config()

    container = build(reg.all())
    assert container.get(Config) is container.get(Config)

    reg2 = Registry()

    @provider(scope=Scope.TRANSIENT, into=reg2)
    def make_fresh() -> Config:
        return Config()

    container2 = build(reg2.all())
    assert container2.get(Config) is not container2.get(Config)


def test_provider_without_return_annotation_is_rejected():
    with pytest.raises(TypeError, match="return type"):

        @provider
        def make_something():
            return object()


def test_provider_only_runs_when_resolved():
    reg = Registry()
    calls = {"n": 0}

    @provider(scope=Scope.TRANSIENT, into=reg)
    def make_config() -> Config:
        calls["n"] += 1
        return Config()

    container = build(reg.all())
    assert calls["n"] == 0
    container.get(Config)
    container.get(Config)
    assert calls["n"] == 2


class Transport:
    def __init__(self, kind: str) -> None:
        self.kind = kind


def test_named_providers_are_resolvable_by_name():
    reg = Registry()

    @provider(provides=Transport, name="http", into=reg)
    def http_transport() -> Transport:
        return Transport("http")

    @provider(provides=Transport, name="grpc", into=reg)
    def grpc_transport() -> Transport:
        return Transport("grpc")

    container = build(reg.all())
    assert container.get(Transport, name="http").kind == "http"
    assert container.get(Transport, name="grpc").kind == "grpc"
    assert set(container.get_all(Transport)) == {"http", "grpc"}


def test_named_provider_respects_its_scope():
    reg = Registry()

    @provider(provides=Transport, name="http", scope=Scope.TRANSIENT, into=reg)
    def http_transport() -> Transport:
        return Transport("http")

    container = build(reg.all())
    assert container.get(Transport, name="http") is not container.get(Transport, name="http")
