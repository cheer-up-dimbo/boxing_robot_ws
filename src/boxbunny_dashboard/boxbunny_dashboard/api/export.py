"""Export endpoints for BoxBunny Dashboard.

Provides CSV and PDF downloads of session data, plus date-range exports.
"""

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from boxbunny_dashboard.api.auth import get_current_user
from boxbunny_dashboard.db.manager import DatabaseManager

logger = logging.getLogger("boxbunny.dashboard.export")
router = APIRouter()


# ---- Helpers ----

def _get_db(request: Request) -> DatabaseManager:
    return request.app.state.db


def _session_to_csv_rows(session: Dict[str, Any]) -> List[Dict[str, str]]:
    """Flatten a session dict into rows suitable for CSV export."""
    rows: List[Dict[str, str]] = []
    # Header row with session metadata
    rows.append({
        "type": "session",
        "session_id": session.get("session_id", ""),
        "mode": session.get("mode", ""),
        "difficulty": session.get("difficulty", ""),
        "started_at": session.get("started_at", ""),
        "ended_at": session.get("ended_at", ""),
        "rounds_completed": str(session.get("rounds_completed", 0)),
        "rounds_total": str(session.get("rounds_total", 0)),
        "value": "",
        "event_type": "",
    })
    # Event rows
    for event in session.get("events", []):
        data_json = event.get("data_json", "{}")
        if isinstance(data_json, str):
            try:
                data = json.loads(data_json)
            except json.JSONDecodeError:
                data = {}
        else:
            data = data_json
        rows.append({
            "type": "event",
            "session_id": session.get("session_id", ""),
            "mode": "",
            "difficulty": "",
            "started_at": "",
            "ended_at": "",
            "rounds_completed": "",
            "rounds_total": "",
            "value": json.dumps(data),
            "event_type": event.get("event_type", ""),
        })
    return rows


def _build_csv_stream(rows: List[Dict[str, str]]) -> io.StringIO:
    """Build a CSV file from a list of row dicts."""
    if not rows:
        output = io.StringIO()
        output.write("No data available\n")
        output.seek(0)
        return output

    output = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return output


def _build_html_report(session: Dict[str, Any]) -> str:
    """Build a simple HTML report for a session (used for PDF fallback)."""
    summary_raw = session.get("summary_json", "{}")
    if isinstance(summary_raw, str):
        try:
            summary = json.loads(summary_raw)
        except json.JSONDecodeError:
            summary = {}
    else:
        summary = summary_raw

    events = session.get("events", [])
    event_rows = ""
    for e in events[:50]:  # cap at 50 events for readability
        event_rows += (
            f"<tr><td>{e.get('timestamp', '')}</td>"
            f"<td>{e.get('event_type', '')}</td></tr>\n"
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>BoxBunny Session Report</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 2em; }}
  h1 {{ color: #e63946; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1em; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
  th {{ background: #f8f9fa; }}
</style></head><body>
<h1>BoxBunny Training Report</h1>
<p><strong>Session:</strong> {session.get('session_id', 'N/A')}</p>
<p><strong>Mode:</strong> {session.get('mode', 'N/A')} |
   <strong>Difficulty:</strong> {session.get('difficulty', 'N/A')}</p>
<p><strong>Started:</strong> {session.get('started_at', 'N/A')} |
   <strong>Ended:</strong> {session.get('ended_at', 'N/A')}</p>
<p><strong>Rounds:</strong> {session.get('rounds_completed', 0)} / {session.get('rounds_total', 0)}</p>
<h2>Summary</h2>
<pre>{json.dumps(summary, indent=2)}</pre>
<h2>Events ({len(events)} total)</h2>
<table><tr><th>Timestamp</th><th>Event Type</th></tr>
{event_rows}</table>
</body></html>"""


# ---- Endpoints ----

@router.get("/session/{session_id}/csv")
async def export_session_csv(
    session_id: str,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> StreamingResponse:
    """Download a CSV file for a specific training session."""
    username = user["username"]
    detail = db.get_session_detail(username, session_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    rows = _session_to_csv_rows(detail)
    stream = _build_csv_stream(rows)
    filename = f"boxbunny_session_{session_id}.csv"

    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/session/{session_id}/pdf")
async def export_session_pdf(
    session_id: str,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
) -> StreamingResponse:
    """Download an HTML report for a session (printable as PDF)."""
    username = user["username"]
    detail = db.get_session_detail(username, session_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    html = _build_html_report(detail)
    stream = io.BytesIO(html.encode("utf-8"))
    filename = f"boxbunny_session_{session_id}.html"

    return StreamingResponse(
        stream,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/range")
async def export_date_range(
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(_get_db),
    start_date: str = Query(..., description="Start date (ISO format YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (ISO format YYYY-MM-DD)"),
    mode: Optional[str] = Query(default=None),
) -> StreamingResponse:
    """Export all sessions within a date range as CSV."""
    username = user["username"]

    # Validate date format
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    all_sessions = db.get_session_history(username, limit=10000, mode=mode)
    filtered = [
        s for s in all_sessions
        if s.get("started_at", "")[:10] >= start_date
        and s.get("started_at", "")[:10] <= end_date
    ]

    all_rows: List[Dict[str, str]] = []
    for session in filtered:
        all_rows.extend(_session_to_csv_rows(session))

    stream = _build_csv_stream(all_rows)
    filename = f"boxbunny_export_{start_date}_to_{end_date}.csv"

    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
