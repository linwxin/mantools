import atexit as _atexit
import sys as _sys

from . import _defaults
from ._logger import Core as _Core
from ._logger import Logger as _Logger

__version__ = "0.6.0"

__all__ = ["logger"]

logger = _Logger(
    core=_Core(),
    exception=None,
    depth=0,
    record=False,
    lazy=False,
    colors=False,
    raw=False,
    capture=True,
    patcher=None,
    extra={},
)

if _defaults.LOGURU_AUTOINIT and _sys.stderr:
    logger.add(_sys.stderr)

_atexit.register(logger.remove)