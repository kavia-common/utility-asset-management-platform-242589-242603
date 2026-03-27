"""
Database helpers for the Asset Management backend.

Uses DATABASE_URL env var if present; otherwise defaults to the local Postgres
used by the infrastructure_db container (port 5001).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row


# PUBLIC_INTERFACE
def get_database_url() -> str:
    """Return the database connection string for Postgres."""
    # NOTE: The orchestrator can set DATABASE_URL in the backend container .env.
    # Fallback is the known local dev DB from infrastructure_db/db_connection.txt.
    return os.getenv("DATABASE_URL", "postgresql://appuser:dbuser123@localhost:5001/myapp")


def _get_conn():
    """Create a short-lived psycopg connection with dict row factory."""
    return psycopg.connect(get_database_url(), row_factory=dict_row)


# PUBLIC_INTERFACE
def fetch_all(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute a SELECT and return rows as list of dicts."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            return list(cur.fetchall())


# PUBLIC_INTERFACE
def fetch_one(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Execute a SELECT and return a single row as dict, or None."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            return cur.fetchone()
