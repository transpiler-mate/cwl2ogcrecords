"""Type the small public surface used from the untyped giturlparse package."""

class GitUrlParsed:
    @property
    def valid(self) -> bool: ...

def parse(url: str, check_domain: bool = True) -> GitUrlParsed: ...
