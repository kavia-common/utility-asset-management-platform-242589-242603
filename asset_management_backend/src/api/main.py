from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .db import fetch_all, fetch_one

openapi_tags = [
    {"name": "Health", "description": "Service health and meta endpoints."},
    {"name": "Assets", "description": "Asset registry and health status."},
    {"name": "Inspections", "description": "Inspection logging and history."},
    {"name": "Alerts", "description": "Health-based alerts and acknowledgements."},
    {"name": "Work Orders", "description": "Work order queue linked to alerts/assets."},
]

app = FastAPI(
    title="Utility Asset Management Backend",
    description="Backend API for utility infrastructure asset registry, inspections, alerts, and work orders.",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"], summary="Health check")
def health_check() -> Dict[str, str]:
    """
    Basic health check.

    Returns:
        JSON message indicating service is up.
    """
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get("/assets", tags=["Assets"], summary="List assets")
def list_assets(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    """Return assets from Postgres."""
    return fetch_all(
        """
        SELECT id, asset_tag, name, asset_type, location, health_score, status, created_at, updated_at
        FROM assets
        ORDER BY created_at DESC
        LIMIT %(limit)s
        """,
        {"limit": limit},
    )


# PUBLIC_INTERFACE
@app.get("/assets/{asset_id}", tags=["Assets"], summary="Get asset")
def get_asset(asset_id: str) -> Dict[str, Any]:
    """Return a single asset by id."""
    row = fetch_one(
        """
        SELECT id, asset_tag, name, asset_type, location, health_score, status, created_at, updated_at
        FROM assets
        WHERE id = %(asset_id)s
        """,
        {"asset_id": asset_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    return row


# PUBLIC_INTERFACE
@app.get("/inspections", tags=["Inspections"], summary="List inspections")
def list_inspections(asset_id: Optional[str] = None, limit: int = Query(200, ge=1, le=500)) -> List[Dict[str, Any]]:
    """Return inspections, optionally filtered by asset."""
    if asset_id:
        return fetch_all(
            """
            SELECT i.id, i.asset_id, a.asset_tag, i.inspector_name, i.inspection_date, i.notes, i.observed_health_score, i.created_at
            FROM inspections i
            JOIN assets a ON a.id = i.asset_id
            WHERE i.asset_id = %(asset_id)s
            ORDER BY i.inspection_date DESC
            LIMIT %(limit)s
            """,
            {"asset_id": asset_id, "limit": limit},
        )
    return fetch_all(
        """
        SELECT i.id, i.asset_id, a.asset_tag, i.inspector_name, i.inspection_date, i.notes, i.observed_health_score, i.created_at
        FROM inspections i
        JOIN assets a ON a.id = i.asset_id
        ORDER BY i.inspection_date DESC
        LIMIT %(limit)s
        """,
        {"limit": limit},
    )


# PUBLIC_INTERFACE
@app.get("/alerts", tags=["Alerts"], summary="List alerts")
def list_alerts(
    asset_id: Optional[str] = None,
    unacknowledged_only: bool = False,
    limit: int = Query(200, ge=1, le=500),
) -> List[Dict[str, Any]]:
    """Return alerts, optionally filtered by asset and acknowledgement status."""
    where_clauses = []
    params: Dict[str, Any] = {"limit": limit}

    if asset_id:
        where_clauses.append("al.asset_id = %(asset_id)s")
        params["asset_id"] = asset_id
    if unacknowledged_only:
        where_clauses.append("al.is_acknowledged = FALSE")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    return fetch_all(
        f"""
        SELECT al.id, al.asset_id, a.asset_tag, al.severity, al.alert_type, al.message,
               al.health_score_at_alert, al.is_acknowledged, al.created_at
        FROM alerts al
        JOIN assets a ON a.id = al.asset_id
        {where_sql}
        ORDER BY al.created_at DESC
        LIMIT %(limit)s
        """,
        params,
    )


# PUBLIC_INTERFACE
@app.get("/work-orders", tags=["Work Orders"], summary="List work orders")
def list_work_orders(
    status: Optional[str] = None,
    limit: int = Query(200, ge=1, le=500),
) -> List[Dict[str, Any]]:
    """Return work orders, optionally filtered by status."""
    params: Dict[str, Any] = {"limit": limit}
    where_sql = ""
    if status:
        where_sql = "WHERE wo.status = %(status)s"
        params["status"] = status

    return fetch_all(
        f"""
        SELECT wo.id, wo.asset_id, a.asset_tag, wo.alert_id, wo.title, wo.description,
               wo.priority, wo.status, wo.due_date, wo.created_at, wo.updated_at
        FROM work_orders wo
        JOIN assets a ON a.id = wo.asset_id
        {where_sql}
        ORDER BY wo.created_at DESC
        LIMIT %(limit)s
        """,
        params,
    )
