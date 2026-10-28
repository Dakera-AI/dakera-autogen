"""AutoGen integration for the Dakera AI memory platform."""

from typing import Any

from autogen_dakera.entities import DakeraEntityExtractor
from autogen_dakera.knowledge_graph import DakeraKnowledgeGraph
from autogen_dakera.memory import DakeraMemory
from autogen_dakera.namespaces import DakeraNamespaceManager
from autogen_dakera.sessions import DakeraSessionManager

__all__ = [
    "DakeraEntityExtractor",
    "DakeraKnowledgeGraph",
    "DakeraMemory",
    "DakeraNamespaceManager",
    "DakeraSessionManager",
]
__version__ = "0.4.0"

try:
    from autogen_dakera.autogen_memory import DakeraAutoGenMemory, DakeraAutoGenMemoryConfig
except ImportError as _error:  # autogen-core or httpx (the ``autogen`` extra) is missing
    _autogen_import_error = _error

    def __getattr__(name: str) -> Any:
        if name in ("DakeraAutoGenMemory", "DakeraAutoGenMemoryConfig"):
            raise ImportError(
                f"{name} needs the autogen extra: pip install 'autogen-dakera[autogen]'"
            ) from _autogen_import_error
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
else:
    __all__ += ["DakeraAutoGenMemory", "DakeraAutoGenMemoryConfig"]
