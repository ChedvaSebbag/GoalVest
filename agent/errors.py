"""שגיאות ההערכה. כשל תשתית לא נרשם ככישלון סופי."""


class InfrastructureError(Exception):
    def __init__(self, service: str, message: str = "") -> None:
        self.service = service
        super().__init__(message or service)


class FormatError(Exception):
    """המודל החזיר פלט שלא עבר פענוח או ולידציה."""


_CONNECTION_NAMES = frozenset({
    "ConnectError",
    "ConnectionError",
    "Timeout",
    "TimeoutError",
    "ReadTimeout",
    "ConnectTimeout",
    "APIConnectionError",
    "URLError",
    "NewConnectionError",
    "ConnectionRefusedError",
})


def as_infrastructure(exc: BaseException, service: str) -> InfrastructureError | None:
    if isinstance(exc, InfrastructureError):
        return exc
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return InfrastructureError(service, str(exc))
    if type(exc).__name__ in _CONNECTION_NAMES:
        return InfrastructureError(service, str(exc))
    text = str(exc).lower()
    if "connection refused" in text or "failed to connect" in text or "errno" in text and "connect" in text:
        return InfrastructureError(service, str(exc))
    return None
