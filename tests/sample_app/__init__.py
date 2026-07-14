"""A tiny package used to exercise recursive component scanning.

Interfaces live here; implementations are spread across submodules so the scan
has to import more than the top-level package.
"""


class Clock:
    def now(self) -> str:
        raise NotImplementedError


class Greeter:
    def greet(self) -> str:
        raise NotImplementedError


class Settings:
    def __init__(self, env: str) -> None:
        self.env = env
