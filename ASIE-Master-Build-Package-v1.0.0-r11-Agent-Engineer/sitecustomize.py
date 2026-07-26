from __future__ import annotations

import functools
import warnings
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])
PY312_DEPRECATED_COMPAT_ID = "ASIE-PY312-DEPRECATED-COMPAT-v1"


def _compat_deprecated(reason: str, /, *, category: type[Warning] = DeprecationWarning, stacklevel: int = 1) -> Callable[[F], F]:
    """Backport the Python 3.13 warnings.deprecated decorator for Python 3.12.

    ASIE r11 local environments may run Python 3.12 while asie_local_api.py
    imports `warnings.deprecated`, which is only available in newer Python
    runtimes. This startup shim adds a minimal compatible decorator before
    backend modules are imported. It does not alter AAS runtime files.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(reason, category, stacklevel=stacklevel + 1)
            return func(*args, **kwargs)

        setattr(wrapper, "__deprecated__", reason)
        return wrapper  # type: ignore[return-value]

    return decorator


if not hasattr(warnings, "deprecated"):
    warnings.deprecated = _compat_deprecated  # type: ignore[attr-defined]
