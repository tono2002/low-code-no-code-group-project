"""
Simulated SAP / ERP connection (mock).

This is NOT a real SAP system — it imitates an SAP S/4HANA OData feed using
authentic SAP field names (LIFNR, EBELN, EBELP, MATNR, WERKS, MENGE, NETPR,
EINDT, LABST ...) so a demo looks credible. In production you would point a real
connector at your S/4HANA OData service (env SAP_BASE_URL) and authenticate with
OAuth2; here the data is generated locally and clearly labelled "simulated".

SAP objects modelled (flattened):
  - LFA1  : vendor master            (LIFNR, NAME1, LAND1)
  - EKKO/EKPO : purchase orders      (EBELN, EBELP, MATNR, MENGE, NETPR, WERKS, EINDT)
  - MARD  : plant stock              (MATNR, WERKS, LABST, safety stock)
"""

import os

import numpy as np

SAP_BASE_URL = os.environ.get("SAP_BASE_URL", "")  # empty → use the local mock

_COUNTRIES = ["DE", "CN", "TW", "MX", "VN", "US", "PL", "IN"]
_HIGH_RISK = {"TW", "VN", "IN"}
_PLANTS = ["1000", "1100", "1200", "1300", "1400"]
_MATERIALS = [
    ("CNC spindle", "EA"), ("Servo motor", "EA"), ("PLC board", "EA"),
    ("Bearing assembly", "EA"), ("Hydraulic valve", "EA"), ("Wiring harness", "M"),
    ("Steel casting", "KG"), ("Sensor module", "EA"), ("Gearbox", "EA"),
    ("Coolant pump", "EA"),
]
_FIRST = ["Apex", "Nordic", "Vertex", "Summit", "Pioneer", "Iron", "Delta",
          "Meridian", "Atlas", "Crown", "Pacific", "Zenith"]
_LAST = ["GmbH", "Industries", "Mfg Co", "Systems", "Engineering", "Metalworks"]


def simulate_connection(seed: int | None = None) -> dict:
    """Return a (simulated) SAP connection handshake."""
    target = SAP_BASE_URL or "sap-s4h.simulated.local:44300 (mock)"
    return {
        "status": "connected",
        "simulated": True,
        "system_id": "S4H",
        "client": "100",
        "host": target,
        "protocol": "OData V2 (simulated)",
        "auth": "OAuth2 client-credentials (mock)",
        "modules": ["MM (Materials Mgmt)", "SD (Sales & Distribution)", "LE (Logistics)"],
        "note": "SIMULATED connection — no real SAP system is contacted.",
    }


def generate_erp_data(seed: int | None = None, n_vendors: int = 8, n_pos: int = 16) -> dict:
    """Generate SAP-shaped supply-chain data (vendors, purchase orders, stock)."""
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 1_000_000))
    rng = np.random.default_rng(seed)

    vendors = []
    for i in range(n_vendors):
        vendors.append({
            "LIFNR": f"0000{10000 + int(rng.integers(1, 8999))}",
            "NAME1": f"{_FIRST[i % len(_FIRST)]} {rng.choice(_LAST)}",
            "LAND1": str(rng.choice(_COUNTRIES)),
            "on_time_rate": round(float(np.clip(rng.normal(0.9, 0.08), 0.45, 0.999)), 3),
        })

    pos = []
    for j in range(n_pos):
        v = vendors[int(rng.integers(0, n_vendors))]
        mat, unit = _MATERIALS[int(rng.integers(0, len(_MATERIALS)))]
        menge = int(rng.integers(5, 500))
        netpr = round(float(rng.uniform(50, 9000)), 2)
        delay = int(np.clip(rng.normal(2 if v["on_time_rate"] > 0.85 else 9, 6), -3, 40))
        pos.append({
            "EBELN": f"45000{10000 + j}",
            "EBELP": f"{(j % 5 + 1) * 10:05d}",
            "LIFNR": v["LIFNR"],
            "MATNR": f"MAT-{1000 + (j % len(_MATERIALS))}",
            "TXZ01": mat,
            "MENGE": menge,
            "MEINS": unit,
            "NETPR": netpr,
            "WERKS": str(rng.choice(_PLANTS)),
            "EINDT": f"2026-{int(rng.integers(6,10)):02d}-{int(rng.integers(1,28)):02d}",
            "delay_days": delay,
            "on_time": bool(delay <= 0),
            "net_value_usd": round(menge * netpr, 2),
        })

    stock = []
    for k, (mat, unit) in enumerate(_MATERIALS[:8]):
        labst = int(rng.integers(0, 2000))
        safety = int(rng.integers(200, 800))
        stock.append({
            "MATNR": f"MAT-{1000 + k}", "TXZ01": mat, "MEINS": unit,
            "WERKS": str(rng.choice(_PLANTS)),
            "LABST": labst, "safety_stock": safety,
            "below_safety": bool(labst < safety),
        })

    # Bake in clear problems for the demo.
    crit_v = vendors[int(rng.integers(0, n_vendors))]
    crit_v["LAND1"] = str(rng.choice(list(_HIGH_RISK)))
    crit_v["on_time_rate"] = round(float(rng.uniform(0.55, 0.66)), 3)
    big_po = max(pos, key=lambda p: p["net_value_usd"])
    big_po.update(LIFNR=crit_v["LIFNR"], delay_days=int(rng.integers(18, 35)), on_time=False)
    stock[0]["LABST"] = 0
    stock[0]["below_safety"] = True

    open_value = round(sum(p["net_value_usd"] for p in pos), 2)
    late_value = round(sum(p["net_value_usd"] for p in pos if not p["on_time"]), 2)
    summary = {
        "vendors": len(vendors),
        "open_pos": len(pos),
        "open_po_value_usd": open_value,
        "late_po_value_usd": late_value,
        "late_po_pct": round(100 * late_value / open_value, 1) if open_value else 0,
        "vendors_below_85pct_otd": sum(1 for v in vendors if v["on_time_rate"] < 0.85),
        "high_risk_country_vendors": sum(1 for v in vendors if v["LAND1"] in _HIGH_RISK),
        "materials_below_safety_stock": sum(1 for s in stock if s["below_safety"]),
        "worst_vendor": min(vendors, key=lambda v: v["on_time_rate"])["NAME1"],
    }
    return {"seed": seed, "connection": simulate_connection(seed),
            "vendors": vendors, "purchase_orders": pos, "stock": stock,
            "summary": summary}


def erp_to_text(data: dict) -> str:
    """Compact SAP-style rendering for the LLM."""
    s = data["summary"]
    head = (
        f"SAP S/4HANA (SIMULATED) — supply-chain extract\n"
        f"KPIs: ${s['open_po_value_usd']:,}/open-PO value · "
        f"${s['late_po_value_usd']:,} late ({s['late_po_pct']}%) · "
        f"{s['vendors_below_85pct_otd']}/{s['vendors']} vendors <85% OTD · "
        f"{s['high_risk_country_vendors']} vendors in high-risk countries · "
        f"{s['materials_below_safety_stock']} materials below safety stock.\n\n"
        "VENDORS (LFA1):\n| LIFNR | NAME1 | LAND1 | OTD% |\n|---|---|---|---|\n"
        + "\n".join(f"| {v['LIFNR']} | {v['NAME1']} | {v['LAND1']} | {round(v['on_time_rate']*100,1)} |"
                    for v in data["vendors"])
        + "\n\nOPEN PURCHASE ORDERS (EKKO/EKPO):\n"
        "| EBELN | LIFNR | MATNR | TXZ01 | MENGE | NETPR | WERKS | EINDT | delay(d) | value $ |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        + "\n".join(
            f"| {p['EBELN']} | {p['LIFNR']} | {p['MATNR']} | {p['TXZ01']} | {p['MENGE']} | "
            f"{p['NETPR']} | {p['WERKS']} | {p['EINDT']} | {p['delay_days']} | {p['net_value_usd']:,} |"
            for p in data["purchase_orders"])
        + "\n\nPLANT STOCK (MARD):\n| MATNR | TXZ01 | WERKS | LABST | safety | below_safety |\n|---|---|---|---|---|---|\n"
        + "\n".join(
            f"| {x['MATNR']} | {x['TXZ01']} | {x['WERKS']} | {x['LABST']} | {x['safety_stock']} | "
            f"{'YES' if x['below_safety'] else 'no'} |" for x in data["stock"])
    )
    return head
