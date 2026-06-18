"""
Simulated ERP connectors (SAP S/4HANA · Odoo · Microsoft Dynamics 365).

NONE of these contact a real ERP — they imitate each system's API + authentic
field names so a demo looks credible, and normalise into the workspace shape
(see app/workspace.py). In production a real connector would be pointed at the
system via env (e.g. SAP_BASE_URL / ODOO_URL / DYNAMICS_URL) and authenticated.

Field flavours:
  SAP      : LFA1 (LIFNR/NAME1/LAND1), EKKO/EKPO (EBELN/MATNR/MENGE/NETPR/WERKS/EINDT)
  Odoo     : res.partner, purchase.order (name/partner_id/product_id/product_qty/price_unit)
  Dynamics : VendVendorV2 (VendorAccount), PurchPurchaseOrderHeader (PurchId/ItemId/PurchQty)
"""

import os

import numpy as np

from .dataset import _risk_score

_COUNTRIES = ["DE", "CN", "TW", "MX", "VN", "US", "PL", "IN"]
_HIGH_RISK = {"TW", "VN", "IN"}
_MATERIALS = ["CNC spindle", "Servo motor", "PLC board", "Bearing assembly",
              "Hydraulic valve", "Wiring harness", "Steel casting", "Sensor module",
              "Gearbox", "Coolant pump"]
_FIRST = ["Apex", "Nordic", "Vertex", "Summit", "Pioneer", "Iron", "Delta",
          "Meridian", "Atlas", "Crown", "Pacific", "Zenith"]
_LAST = ["GmbH", "Industries", "Mfg Co", "Systems", "Engineering", "Metalworks"]

SYSTEMS = {
    "sap": {
        "label": "SAP S/4HANA (simulated)", "system_id": "S4H", "client": "100",
        "protocol": "OData V2 (simulated)", "auth": "OAuth2 client-credentials (mock)",
        "env": "SAP_BASE_URL", "default_host": "sap-s4h.simulated.local:44300 (mock)",
        "modules": ["MM (Materials Mgmt)", "SD (Sales & Distribution)", "LE (Logistics)"],
        "po_cols": ["EBELN", "LIFNR", "MATNR", "TXZ01", "MENGE", "NETPR", "WERKS", "EINDT", "delay(d)", "value $"],
    },
    "odoo": {
        "label": "Odoo (simulated)", "system_id": "odoo-prod", "client": "db: titan",
        "protocol": "JSON-RPC (simulated)", "auth": "API key (mock)",
        "env": "ODOO_URL", "default_host": "titan.odoo.simulated (mock)",
        "modules": ["purchase", "stock", "product"],
        "po_cols": ["name", "partner_id", "product_id", "product_qty", "price_unit", "picking_type_id", "date_planned", "delay(d)", "amount $"],
    },
    "dynamics": {
        "label": "Microsoft Dynamics 365 (simulated)", "system_id": "D365FO", "client": "DAT",
        "protocol": "OData v4 (simulated)", "auth": "Azure AD OAuth2 (mock)",
        "env": "DYNAMICS_URL", "default_host": "titan.operations.dynamics.simulated (mock)",
        "modules": ["Procurement & sourcing", "Inventory mgmt", "Supply chain"],
        "po_cols": ["PurchId", "VendorAccount", "ItemId", "Name", "PurchQty", "PurchPrice", "InventSiteId", "DeliveryDate", "delay(d)", "LineAmount $"],
    },
}


def simulate_connection(system: str = "sap") -> dict:
    cfg = SYSTEMS.get(system, SYSTEMS["sap"])
    host = os.environ.get(cfg["env"], "") or cfg["default_host"]
    return {"status": "connected", "simulated": True, "system": system,
            "label": cfg["label"], "system_id": cfg["system_id"], "client": cfg["client"],
            "host": host, "protocol": cfg["protocol"], "auth": cfg["auth"],
            "modules": cfg["modules"],
            "note": f"SIMULATED {cfg['label']} connection — no real system is contacted."}


def generate_erp_data(system: str = "sap", seed: int | None = None,
                      n_vendors: int = 8, n_pos: int = 16) -> dict:
    cfg = SYSTEMS.get(system, SYSTEMS["sap"])
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 1_000_000))
    rng = np.random.default_rng(seed)

    vendors = []
    for i in range(n_vendors):
        vendors.append({
            "id": f"{10000 + int(rng.integers(1, 8999))}",
            "name": f"{_FIRST[i % len(_FIRST)]} {rng.choice(_LAST)}",
            "country": str(rng.choice(_COUNTRIES)),
            "on_time_rate": round(float(np.clip(rng.normal(0.9, 0.08), 0.45, 0.999)), 3),
            "open_po_usd": 0.0,
        })

    pos = []
    for j in range(n_pos):
        v = vendors[int(rng.integers(0, n_vendors))]
        menge = int(rng.integers(5, 500))
        netpr = round(float(rng.uniform(50, 9000)), 2)
        delay = int(np.clip(rng.normal(2 if v["on_time_rate"] > 0.85 else 9, 6), -3, 40))
        value = round(menge * netpr, 2)
        v["open_po_usd"] += value
        pos.append({"id": f"45000{10000 + j}", "vendor": v, "matnr": f"MAT-{1000 + (j % len(_MATERIALS))}",
                    "material": _MATERIALS[j % len(_MATERIALS)], "qty": menge, "price": netpr,
                    "plant": str(rng.choice(["1000", "1100", "1200", "1300"])),
                    "eindt": f"2026-{int(rng.integers(6,10)):02d}-{int(rng.integers(1,28)):02d}",
                    "delay_days": delay, "value": value})

    # Bake in clear problems.
    crit = vendors[int(rng.integers(0, n_vendors))]
    crit.update(country=str(rng.choice(list(_HIGH_RISK))), on_time_rate=round(float(rng.uniform(0.55, 0.66)), 3))
    big = max(pos, key=lambda p: p["value"])
    big["delay_days"] = int(rng.integers(18, 35))

    # Canonical suppliers (for risk + logistics).
    suppliers = []
    for v in vendors:
        rec = {"supplier": v["name"], "region": v["country"], "tier": 1,
               "on_time_rate": v["on_time_rate"], "lead_time_cov": 0.2,
               "annual_spend_musd": round(v["open_po_usd"] / 1e6, 3),
               "single_source": False}
        rec["risk_score"] = round(_risk_score(rec), 1)
        suppliers.append(rec)
    suppliers.sort(key=lambda s: s["risk_score"], reverse=True)

    # UI table = purchase orders, headers in the system's field names.
    rows = [[p["id"], p["vendor"]["id"] if system != "odoo" else p["vendor"]["name"],
             p["matnr"], p["material"], p["qty"], p["price"], p["plant"], p["eindt"],
             p["delay_days"], round(p["value"], 0)] for p in pos]
    open_val = round(sum(p["value"] for p in pos), 0)
    late_val = round(sum(p["value"] for p in pos if p["delay_days"] > 0), 0)
    summary = {
        "vendors": n_vendors, "open_pos": n_pos,
        "open_po_value_usd": open_val, "late_po_value_usd": late_val,
        "late_po_pct": round(100 * late_val / open_val, 1) if open_val else 0,
        "vendors_below_85pct_otd": sum(1 for v in vendors if v["on_time_rate"] < 0.85),
        "high_risk_country_vendors": sum(1 for v in vendors if v["country"] in _HIGH_RISK),
        "worst_vendor": min(vendors, key=lambda v: v["on_time_rate"])["name"],
    }
    text = _erp_to_text(cfg, vendors, pos, summary)
    return {"source": f"erp:{system}", "label": cfg["label"], "seed": seed,
            "connection": simulate_connection(system), "summary": summary,
            "table": {"columns": cfg["po_cols"], "rows": rows},
            "suppliers": suppliers, "text": text}


def _erp_to_text(cfg, vendors, pos, s):
    head = (
        f"{cfg['label']} — supply-chain extract\n"
        f"KPIs: ${s['open_po_value_usd']:,.0f} open-PO value · ${s['late_po_value_usd']:,.0f} late "
        f"({s['late_po_pct']}%) · {s['vendors_below_85pct_otd']}/{s['vendors']} vendors <85% OTD · "
        f"{s['high_risk_country_vendors']} in high-risk countries.\n\n"
        "VENDORS:\n| id | name | country | OTD% | open PO $ |\n|---|---|---|---|---|\n"
        + "\n".join(f"| {v['id']} | {v['name']} | {v['country']} | {round(v['on_time_rate']*100,1)} | {v['open_po_usd']:,.0f} |"
                    for v in vendors)
        + "\n\nOPEN PURCHASE ORDERS:\n| PO | vendor | material | qty | price | plant | due | delay(d) | value $ |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        + "\n".join(f"| {p['id']} | {p['vendor']['name']} | {p['material']} | {p['qty']} | {p['price']} | "
                    f"{p['plant']} | {p['eindt']} | {p['delay_days']} | {p['value']:,.0f} |" for p in pos)
    )
    return head
