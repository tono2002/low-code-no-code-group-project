"""
Single shared in-memory workspace (fits the shared-password model).

Holds the currently loaded data source, its normalised representation, the
computed logistics-risk layer, the last analysis, and the chat history. Replaced
whenever a new source is loaded. Guarded by a lock for concurrent access.

Normalised shape (what every data source produces):
  {
    "source": "synthetic" | "upload" | "erp:sap" | "erp:odoo" | "erp:dynamics",
    "label":  human label,
    "seed":   int | None,
    "summary": {chip_label: value, ...},      # KPI chips for the UI
    "table":  {"columns": [...], "rows": [[...]]},   # capped, for the UI table
    "suppliers": [ {region, annual_spend_musd, on_time_rate, ...} ] | None,
    "text":   markdown the LLM analyses,
    "logistics": {"shipments": [...], "summary": {...}},
    "analysis_md": str | None,
    "chat": [ {"role": "user"|"assistant", "content": str} ],
    "loaded": bool,
  }
"""

import threading

_lock = threading.Lock()
_WS: dict = {"loaded": False, "chat": []}

CHAT_CAP = 24


def set_workspace(data: dict) -> None:
    """Replace the workspace with a freshly loaded source (resets analysis/chat)."""
    with _lock:
        _WS.clear()
        _WS.update(data)
        _WS["analysis_md"] = None
        _WS["chat"] = []
        _WS["loaded"] = True


def get_workspace() -> dict:
    with _lock:
        return dict(_WS)


def set_analysis(markdown: str) -> None:
    with _lock:
        _WS["analysis_md"] = markdown


def append_chat(role: str, content: str) -> None:
    with _lock:
        _WS.setdefault("chat", []).append({"role": role, "content": content})
        _WS["chat"] = _WS["chat"][-CHAT_CAP:]


def is_loaded() -> bool:
    with _lock:
        return bool(_WS.get("loaded"))
