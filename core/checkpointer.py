"""LangGraph Checkpointer -- PostgreSQL persistent state

Connection: same PostgreSQL as Langfuse, separate 'autopipe' database
Fallback: MemorySaver if PostgreSQL unavailable
"""

import os
import logging
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

_DB_URI = os.environ.get(
    "AUTOPIPE_DATABASE_URL",
    "postgresql://langfuse:langfuse@localhost:5432/autopipe",
)

_checkpointer = None


def get_checkpointer():
    """Get or create the checkpointer singleton.

    Tries PostgreSQL first, falls back to MemorySaver.
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg import connect

        # Test connection
        conn = connect(_DB_URI, autocommit=True)
        conn.close()

        # PostgresSaver with direct connection (not context manager)
        checkpointer = PostgresSaver(connect(_DB_URI, autocommit=True))
        checkpointer.setup()
        _checkpointer = checkpointer
        logger.info(f"[Checkpointer] PostgreSQL connected: {_DB_URI.split('@')[1]}")
    except Exception as e:
        logger.warning(f"[Checkpointer] PostgreSQL unavailable ({e}), using MemorySaver")
        _checkpointer = MemorySaver()

    return _checkpointer
