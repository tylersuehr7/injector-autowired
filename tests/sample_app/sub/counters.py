from injector_autowired import Scope, component


@component(scope=Scope.TRANSIENT)
class Counter:
    """Lives in a subpackage to prove the scan recurses."""

    def __init__(self) -> None:
        self.value = 0
