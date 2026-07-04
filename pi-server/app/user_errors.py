"""Format exceptions for user-visible UI error messages."""


def format_user_error(exc: BaseException) -> str:
    """Return a safe, readable error string — never swallow details silently."""
    message = str(exc).strip()
    if message:
        return message
    return f"{exc.__class__.__name__} (no details)"
