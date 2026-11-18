"""Small window for the Wataniya load API.

Start the API first, then:

    .venv/Scripts/python.exe -m streamlit run ui.py
"""

from __future__ import annotations

import json
import time
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

RUN_COLUMNS = ("created_at", "status", "pipeline", "job", "start_dt", "end_dt", "run_id", "error")


def call(api: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    payload = None if body is None else json.dumps(body).encode()
    request = Request(
        api.rstrip("/") + path,
        data=payload,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode()
        try:
            parsed = json.loads(detail)
            detail = parsed.get("detail", detail)
        except json.JSONDecodeError:
            pass
        return exc.code, {"detail": detail}
    except URLError as exc:
        return 0, {"detail": str(exc.reason)}
    except TimeoutError:
        return 0, {"detail": "The API did not answer within 30 seconds"}


st.set_page_config(page_title="Wataniya ETL", layout="wide")
st.title("Wataniya ETL")

api = st.sidebar.text_input("API", value="http://127.0.0.1:8000")
health_code, health = call(api, "GET", "/health")
if health_code == 200:
    st.sidebar.success("API ok")
else:
    st.sidebar.error(health.get("detail") or "API unavailable")

today = date.today()
left, right = st.columns(2)
start_dt = left.date_input("Start", value=today.replace(day=1))
end_dt = right.date_input("End", value=today)

if st.button("Run full pipeline", type="primary", disabled=health_code != 200):
    code, payload = call(
        api,
        "POST",
        "/jobs/load",
        {"start_dt": start_dt.isoformat(), "end_dt": end_dt.isoformat()},
    )
    if code == 202:
        st.session_state["run_id"] = str(payload["run_id"])
        st.success(f"Accepted {payload['run_id']}")
    else:
        st.error(str(payload.get("detail") or payload))

runs_code, runs_payload = call(api, "GET", "/runs")
runs = runs_payload.get("runs", []) if runs_code == 200 else []
if runs_code not in (0, 200):
    st.error(str(runs_payload.get("detail") or runs_payload))

if not runs:
    st.info("No runs yet.")
    st.stop()

st.subheader("Runs")
st.dataframe(
    [{column: row.get(column) for column in RUN_COLUMNS} for row in runs],
    use_container_width=True,
    hide_index=True,
)

run_ids = [str(row["run_id"]) for row in runs]
selected = st.session_state.get("run_id")
chosen = st.selectbox("Run", run_ids, index=run_ids.index(selected) if selected in run_ids else 0)
detail_code, detail = call(api, "GET", f"/runs/{chosen}")
if detail_code != 200:
    st.error(str(detail.get("detail") or detail))
    st.stop()

status = str(detail.get("status") or "")
st.write(f"Status: **{status}**")
if detail.get("error"):
    st.error(detail["error"])

events = detail.get("events") or []
if events:
    st.dataframe(events, use_container_width=True, hide_index=True)
else:
    st.caption("No events yet.")

if status in {"queued", "running"}:
    st.caption("This page refreshes every 5 seconds while the run is active.")
    time.sleep(5)
    st.rerun()
