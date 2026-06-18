"""
Simulated logistics-risk layer (numpy, seeded).

Turns the loaded suppliers into in-transit shipments and scores each for delay /
disruption risk: transport mode (Sea/Air/Road/Rail), lane, carrier, ETA, weather
risk, port congestion, value at risk and the expected delay cost. This is the
"flights/ships potentially delayed + cost" dimension of the analysis.

CLEARLY SIMULATED — no live AIS / flight / weather feeds are contacted. In
production a connector would populate these from real APIs (env *_API_URL).
"""

import numpy as np

_MODES = ["Sea", "Air", "Road", "Rail"]
_MODE_P = [0.5, 0.2, 0.22, 0.08]
_TRANSIT = {"Sea": (18, 45), "Air": (2, 6), "Road": (3, 12), "Rail": (8, 20)}
_CARRIERS = {
    "Sea": ["Maersk", "MSC", "CMA CGM", "Hapag-Lloyd"],
    "Air": ["Lufthansa Cargo", "FedEx", "DHL Aviation", "Emirates SkyCargo"],
    "Road": ["DB Schenker", "DSV", "Kuehne+Nagel"],
    "Rail": ["DB Cargo", "China Railway Express"],
}
_HIGH_RISK = {"TW", "Taiwan", "VN", "Vietnam", "IN", "India", "CN", "China"}
_DEST_PLANTS = ["Plant 1000 (DE)", "Plant 1100 (DE)", "Plant 1200 (PL)", "Plant 1300 (MX)"]


def generate_logistics(seed: int | None = None, suppliers: list | None = None,
                       n: int = 14) -> dict:
    """Generate simulated in-transit shipments with delay-risk scoring."""
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 1_000_000))
    rng = np.random.default_rng(seed + 7)  # offset so it differs from the dataset seed

    shipments = []
    for i in range(n):
        sup = suppliers[i % len(suppliers)] if suppliers else None
        origin = (sup or {}).get("region") or str(rng.choice(
            ["DE", "CN", "TW", "MX", "VN", "US", "PL", "IN"]))
        mode = str(rng.choice(_MODES, p=_MODE_P))
        lo, hi = _TRANSIT[mode]
        eta_days = int(rng.integers(lo, hi))
        weather = round(float(np.clip(rng.beta(2, 5), 0, 1)), 2)
        port = round(float(np.clip(rng.beta(2, 4) if mode == "Sea" else rng.beta(1.5, 6), 0, 1)), 2)
        region_risk = 0.2 if origin in _HIGH_RISK else 0.0
        mode_risk = {"Sea": 0.12, "Air": 0.06, "Road": 0.08, "Rail": 0.1}[mode]
        delay_prob = round(float(np.clip(weather * 0.4 + port * 0.4 + region_risk + mode_risk
                                         + rng.normal(0, 0.05), 0.02, 0.97)), 2)
        # value in transit: tie to supplier spend if available
        spend = (sup or {}).get("annual_spend_musd")
        value = round(float(spend) * 1e6 / 12 if spend else float(rng.uniform(80_000, 1_800_000)), 0)
        exp_delay_days = round(delay_prob * rng.uniform(3, 14), 1)
        # cost: penalty per delayed day as a fraction of shipment value + expediting
        delay_cost = round(value * (0.004 * exp_delay_days) + delay_prob * rng.uniform(5_000, 40_000), 0)
        shipments.append({
            "shipment_id": f"SHP-{100000 + i}",
            "mode": mode,
            "carrier": str(rng.choice(_CARRIERS[mode])),
            "origin": origin,
            "destination": str(rng.choice(_DEST_PLANTS)),
            "supplier": (sup or {}).get("supplier") or (sup or {}).get("NAME1") or "—",
            "eta_days": eta_days,
            "weather_risk": weather,
            "port_congestion": port,
            "delay_probability": delay_prob,
            "value_in_transit_usd": value,
            "expected_delay_days": exp_delay_days,
            "expected_delay_cost_usd": delay_cost,
        })

    shipments.sort(key=lambda s: s["expected_delay_cost_usd"], reverse=True)
    total_value = round(sum(s["value_in_transit_usd"] for s in shipments), 0)
    total_cost = round(sum(s["expected_delay_cost_usd"] for s in shipments), 0)
    high = [s for s in shipments if s["delay_probability"] >= 0.5]
    by_mode = {m: sum(1 for s in shipments if s["mode"] == m) for m in _MODES}
    summary = {
        "shipments": len(shipments),
        "value_in_transit_usd": total_value,
        "expected_delay_cost_usd": total_cost,
        "high_risk_shipments": len(high),
        "by_mode": by_mode,
        "worst_lane": f"{shipments[0]['origin']}→{shipments[0]['destination']} "
                      f"({shipments[0]['mode']})" if shipments else "—",
    }
    return {"seed": seed, "shipments": shipments, "summary": summary, "simulated": True}


def logistics_to_text(log: dict) -> str:
    """Compact markdown of the logistics layer for the LLM."""
    s = log["summary"]
    head = (
        f"LOGISTICS RISK (SIMULATED in-transit shipments)\n"
        f"{s['shipments']} shipments · ${s['value_in_transit_usd']:,.0f} in transit · "
        f"${s['expected_delay_cost_usd']:,.0f} expected delay cost · "
        f"{s['high_risk_shipments']} high-risk (delay prob ≥50%) · "
        f"modes {s['by_mode']} · worst lane {s['worst_lane']}.\n\n"
        "| Shipment | Mode | Carrier | Lane | ETA d | Weather | PortCong | DelayProb | Value $ | Delay cost $ |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = "\n".join(
        f"| {s['shipment_id']} | {s['mode']} | {s['carrier']} | {s['origin']}→{s['destination']} | "
        f"{s['eta_days']} | {s['weather_risk']} | {s['port_congestion']} | {s['delay_probability']} | "
        f"{s['value_in_transit_usd']:,.0f} | {s['expected_delay_cost_usd']:,.0f} |"
        for s in log["shipments"]
    )
    return head + rows
