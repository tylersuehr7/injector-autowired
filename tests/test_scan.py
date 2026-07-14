"""End-to-end scanning of a real package via the single entry point."""

import sys

import pytest

from injector_autowired import get_container, resolve, scan


@pytest.fixture
def fresh_import():
    """Evict the fixture package so scan re-runs its decorators.

    Module imports are cached, so the decorators only run once per process. The
    autouse registry-clearing fixture would otherwise leave later scans with an
    empty registry; dropping the modules forces a genuine re-import. Because the
    re-import produces *new* class objects, tests must import the fixture's
    interfaces after the scan (see the local imports below) so identities line
    up with what the container bound.
    """
    for name in list(sys.modules):
        if name == "tests.sample_app" or name.startswith("tests.sample_app."):
            del sys.modules[name]
    yield


def test_scan_discovers_components_across_submodules(fresh_import):
    container = scan("tests.sample_app", profiles=["prod"])

    from tests.sample_app import Clock, Greeter
    from tests.sample_app.sub.counters import Counter

    assert container.get(Clock).now() == "now"
    # Greeter depends on Clock — wired automatically.
    assert container.get(Greeter).greet() == "hello@now"
    # Counter lives in a subpackage, proving recursion, and is transient.
    assert isinstance(container.get(Counter), Counter)
    assert container.get(Counter) is not container.get(Counter)


def test_scan_honors_active_profiles(fresh_import):
    prod = scan("tests.sample_app", profiles=["prod"])
    from tests.sample_app import Settings

    assert prod.get(Settings).env == "prod"


def test_scan_default_profile_uses_negated_provider(fresh_import):
    dev = scan("tests.sample_app", profiles=["dev"])
    from tests.sample_app import Settings

    assert dev.get(Settings).env == "dev"


def test_scan_sets_the_global_container(fresh_import):
    scan("tests.sample_app", profiles=["prod"])
    from tests.sample_app import Clock, Greeter

    assert resolve(Greeter).greet() == "hello@now"
    assert get_container().get(Clock).now() == "now"


def test_scan_accepts_a_list_of_packages(fresh_import):
    container = scan(["tests.sample_app"], profiles=["prod"])
    from tests.sample_app import Clock

    assert container.get(Clock).now() == "now"


def test_resolve_before_scan_raises():
    import injector_autowired.container as container_module

    container_module._current = None
    with pytest.raises(RuntimeError, match="scan"):
        resolve(object)
