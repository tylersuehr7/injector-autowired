import pytest

from injector_autowired import registry


@pytest.fixture(autouse=True)
def clean_global_registry():
    """Keep the process-wide registry from leaking between tests."""
    registry.clear()
    yield
    registry.clear()
