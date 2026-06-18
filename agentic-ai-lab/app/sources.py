"""
Flexible data-source loaders that normalise into the workspace shape
(see app/workspace.py). Handles arbitrary uploaded CSV/XLSX (auto-detected
columns, even 50+), plus thin adapters for the synthetic dataset.

Uploaded files are UNTRUSTED: size/type are capped in the endpoint; here we
profile the data and best-effort map recognisable supplier columns so the risk
heuristics and logistics layer can use them.
"""

import io
import re
import urllib.request

import numpy as np
import pandas as pd

MAX_ROWS = 50_000          # sample beyond this
MAX_FETCH_BYTES = 25 * 1024 * 1024

# Whitelisted public datasets (no login, freely downloadable). Whitelist = no SSRF.
PUBLIC_DATASETS = {
    "usaid": {
        "label": "USAID Supply Chain Shipment Pricing",
        "url": "https://data.usaid.gov/api/views/a3rc-nmf6/rows.csv?accessType=DOWNLOAD",
        "filename": "usaid_shipment_pricing.csv",
    },
}


def fetch_public_dataset(key: str) -> dict:
    """Download a whitelisted public CSV and parse it like an upload."""
    ds = PUBLIC_DATASETS.get(key)
    if not ds:
        raise ValueError("Unknown public dataset")
    req = urllib.request.Request(ds["url"], headers={"User-Agent": "agentic-ai-lab"})
    with urllib.request.urlopen(req, timeout=30) as r:
        content = r.read(MAX_FETCH_BYTES + 1)
    if len(content) > MAX_FETCH_BYTES:
        raise ValueError("Remote file too large")
    src = parse_upload(ds["filename"], content)
    src["source"] = "public"
    src["label"] = f"Public: {ds['label']}"
    return src
DISPLAY_ROWS = 60          # rows sent to the UI table
LLM_SAMPLE_ROWS = 6        # rows embedded in the LLM text
LLM_SAMPLE_COLS = 16       # columns embedded in the LLM sample

# Fuzzy column-name matchers → canonical supplier fields.
_MATCHERS = {
    "supplier": r"supplier|vendor|partner|lieferant|name1?\b|company",
    "region": r"region|country|land1?|origin|location|nation",
    "on_time": r"on[_\- ]?time|otd|punctual|delivery.?stat|late.?deliv",
    "spend": r"spend|annual.?spend|amount|value|net.?value|cost|sales|price|revenue",
    "lead_time": r"lead.?time|days.?for.?ship|transit|shipping.?days",
    "single_source": r"single.?sourc|sole.?sourc",
}


def _match(columns, key):
    pat = re.compile(_MATCHERS[key], re.IGNORECASE)
    for c in columns:
        if pat.search(str(c)):
            return c
    return None


def synthetic_source(seed: int | None = None, n: int = 12) -> dict:
    """Adapter: the synthetic dataset in the normalised workspace shape."""
    from .dataset import generate_dataset, dataset_to_text
    ds = generate_dataset(seed=seed, n=n)
    cols = ["Supplier", "Tier", "Region", "Component", "On-time%", "Lead d",
            "Lead CoV", "Spend $M", "Single", "Risk"]
    rows = [[x["supplier"], f"T{x['tier']}", x["region"], x["component"],
             round(x["on_time_rate"] * 100, 1), x["avg_lead_time_days"], x["lead_time_cov"],
             x["annual_spend_musd"], "YES" if x["single_source"] else "no", x["risk_score"]]
            for x in ds["suppliers"]]
    return {"source": "synthetic", "label": f"Synthetic dataset (seed {ds['seed']})",
            "seed": ds["seed"], "summary": ds["summary"],
            "table": {"columns": cols, "rows": rows},
            "suppliers": ds["suppliers"], "text": dataset_to_text(ds)}


def parse_upload(filename: str, content: bytes) -> dict:
    """Parse an uploaded CSV/XLSX into the normalised workspace shape."""
    name = (filename or "data").strip().replace("\n", " ")
    lower = name.lower()
    if lower.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), nrows=MAX_ROWS, on_bad_lines="skip")
    elif lower.endswith((".xlsx", ".xlsm")):
        df = pd.read_excel(io.BytesIO(content), nrows=MAX_ROWS, engine="openpyxl")
    else:
        raise ValueError("Unsupported file type — upload a .csv or .xlsx")
    if df.empty or df.shape[1] == 0:
        raise ValueError("The file has no readable tabular data.")
    df.columns = [str(c).strip() for c in df.columns]

    cols = list(df.columns)
    numeric = df.select_dtypes(include="number").columns.tolist()

    # Per-column profile.
    profile = []
    for c in cols:
        s = df[c]
        p = {"name": c, "dtype": str(s.dtype),
             "non_null_pct": round(100 * float(s.notna().mean()), 1),
             "unique": int(s.nunique(dropna=True))}
        if c in numeric and s.notna().any():
            p["min"] = round(float(s.min()), 3)
            p["max"] = round(float(s.max()), 3)
            p["mean"] = round(float(s.mean()), 3)
        else:
            top = s.dropna().astype(str)
            p["example"] = top.iloc[0][:40] if len(top) else ""
        profile.append(p)

    suppliers = _map_suppliers(df, cols, numeric)
    summary = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "numeric_cols": len(numeric),
    }
    if suppliers:
        ot = [s["on_time_rate"] for s in suppliers if s.get("on_time_rate") is not None]
        if ot:
            summary["avg_on_time_pct"] = round(100 * float(np.mean(ot)), 1)
        summary["high_risk_suppliers"] = sum(1 for s in suppliers if s.get("risk_score", 0) >= 55)

    table = {"columns": cols,
             "rows": df.head(DISPLAY_ROWS).astype(object).where(df.notna(), "").values.tolist()}
    text = _upload_to_text(name, df, profile, suppliers)
    return {"source": "upload", "label": f"Uploaded: {name}", "seed": None,
            "summary": summary, "table": table, "suppliers": suppliers, "text": text}


def _map_suppliers(df, cols, numeric):
    """Best-effort mapping of recognised columns to canonical supplier rows."""
    name_c, region_c = _match(cols, "supplier"), _match(cols, "region")
    ot_c, spend_c, ss_c = _match(cols, "on_time"), _match(cols, "spend"), _match(cols, "single_source")
    if not (ot_c or spend_c or region_c):
        return None  # not supplier-shaped enough; keep as generic tabular data

    from .dataset import _risk_score
    rows = df.head(300)
    out = []
    # normalise on-time to a 0-1 rate if numeric
    ot_scale = 1.0
    if ot_c and ot_c in numeric and rows[ot_c].notna().any():
        ot_scale = 100.0 if float(rows[ot_c].max()) > 1.5 else 1.0
    for _, r in rows.iterrows():
        rec = {
            "supplier": str(r[name_c]) if name_c else "supplier",
            "region": str(r[region_c]) if region_c else "—",
            "on_time_rate": (round(float(r[ot_c]) / ot_scale, 3)
                             if ot_c and ot_c in numeric and pd.notna(r[ot_c]) else None),
            "annual_spend_musd": (round(float(r[spend_c]) / 1e6, 3)
                                  if spend_c and spend_c in numeric and pd.notna(r[spend_c]) else None),
            "single_source": (bool(r[ss_c]) if ss_c and pd.notna(r[ss_c]) else False),
            "lead_time_cov": 0.2, "tier": 1,
        }
        # risk needs a few fields; fill gentle defaults when missing
        rec_for_risk = {**rec,
                        "on_time_rate": rec["on_time_rate"] if rec["on_time_rate"] is not None else 0.9,
                        "annual_spend_musd": rec["annual_spend_musd"] if rec["annual_spend_musd"] is not None else 1.0}
        rec["risk_score"] = round(_risk_score(rec_for_risk), 1)
        out.append(rec)
    out.sort(key=lambda s: s.get("risk_score", 0), reverse=True)
    return out


def _upload_to_text(name, df, profile, suppliers):
    lines = [f"UPLOADED DATASET: {name} — {df.shape[0]} rows × {df.shape[1]} columns\n",
             "COLUMN PROFILE:", "| column | dtype | non-null% | unique | range / example |",
             "|---|---|---|---|---|"]
    for p in profile:
        rng = (f"{p['min']}–{p['max']} (mean {p['mean']})" if "mean" in p else p.get("example", ""))
        lines.append(f"| {p['name']} | {p['dtype']} | {p['non_null_pct']} | {p['unique']} | {rng} |")
    sample = df.head(LLM_SAMPLE_ROWS).iloc[:, :LLM_SAMPLE_COLS]
    lines.append("\nSAMPLE ROWS (first columns):")
    lines.append("| " + " | ".join(str(c) for c in sample.columns) + " |")
    lines.append("|" + "---|" * len(sample.columns))
    for _, r in sample.iterrows():
        lines.append("| " + " | ".join(str(v)[:24] for v in r.values) + " |")
    if suppliers:
        lines.append(f"\nRecognised {len(suppliers)} supplier-like rows; "
                     f"top risk: {suppliers[0]['supplier']} (risk {suppliers[0]['risk_score']}).")
    return "\n".join(lines)
