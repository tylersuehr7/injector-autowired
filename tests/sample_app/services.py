from injector_autowired import provider, service

from . import Clock, Greeter, Settings


@service(bind=Clock)
class SystemClock(Clock):
    def now(self) -> str:
        return "now"


@service(bind=Greeter)
class HelloGreeter(Greeter):
    def __init__(self, clock: Clock):  # autowired, no @inject
        self.clock = clock

    def greet(self) -> str:
        return f"hello@{self.clock.now()}"


@provider(profiles=["prod"])
def prod_settings() -> Settings:
    return Settings("prod")


@provider(profiles=["!prod"])
def dev_settings() -> Settings:
    return Settings("dev")
