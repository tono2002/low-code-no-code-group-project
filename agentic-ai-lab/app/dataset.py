"""
Synthetic supply-chain dataset generator (numpy).

Creates a realistic supplier table with a few risk patterns deliberately baked
in (a single-sourced Tier-2 supplier in a high-risk region, a chronically late
high-spend supplier, etc.) so the agent crew has real signal to find. Seeded, so
the same seed reproduces the same dataset — handy for a live demo / presentation.
"""

import numpy as np

REGIONS = ["Germany", "China", "Taiwan", "Mexico", "Vietnam", "USA", "Poland", "India"]
HIGH_RISK_REGIONS = {"Taiwan", "Vietnam", "India"}
COMPONENTS = [
    "CNC spindle", "Servo motor", "PLC board", "Bearing assembly", "Hydraulic valve",
    "Wiring harness", "Steel casting", "Sensor module", "Gearbox", "Power supply unit",
    "Coolant pump", "Linear guide",
]
_FIRST = ["Apex", "Nordic", "Vertex", "Summit", "Pioneer", "Iron", "Delta", "Meridian",
          "Atlas", "Crown", "Pacific", "Zenith", "Orion", "Falcon", "Granite", "Vanguard"]
_LAST = ["Components", "Industries", "Manufacturing", "Systems", "Engineering",
         "Metalworks", "Precision", "Dynamics"]


def _risk_score(s: dict) -> float:
    """0-100 composite risk: lateness, lead-time variability, single-sourcing,
    region risk, weighted by annual spend (financial exposure)."""
    late = (1 - s["on_time_rate"]) * 45
    var = s["lead_time_cov"] * 25
    single = 12 if s["single_source"] else 0
    region = 10 if s["region"] in HIGH_RISK_REGIONS else 0
    tier = 8 if s["tier"] == 2 else 0
    base = late + var + single + region + tier
    # scale by relative spend so big-exposure suppliers rank higher
    return float(np.clip(base * (0.7 + 0.3 * min(s["annual_spend_musd"] / 4, 1.5)), 0, 100))


def generate_dataset(seed: int | None = None, n: int = 12) -> dict:
    """Generate a synthetic supplier dataset. Returns a JSON-able dict."""
    n = int(max(6, min(20, n)))
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 1_000_000))
    rng = np.random.default_rng(seed)

    names = [f"{_FIRST[i % len(_FIRST)]} {rng.choice(_LAST)}" for i in range(n)]
    suppliers = []
    for i in range(n):
        tier = int(rng.choice([1, 2], p=[0.55, 0.45]))
        suppliers.append({
            "supplier": names[i],
            "tier": tier,
            "region": str(rng.choice(REGIONS)),
            "component": str(rng.choice(COMPONENTS)),
            "on_time_rate": round(float(np.clip(rng.normal(0.91, 0.07), 0.45, 0.999)), 3),
            "avg_lead_time_days": int(np.clip(rng.normal(35 if tier == 2 else 21, 9), 5, 90)),
            "lead_time_cov": round(float(np.clip(rng.normal(0.22, 0.10), 0.03, 0.85)), 2),
            "annual_spend_musd": round(float(rng.uniform(0.2, 6.0)), 2),
            "single_source": bool(rng.random() < (0.45 if tier == 2 else 0.18)),
        })

    # Bake in two clear problems so the demo always has something to find.
    crit = suppliers[int(rng.integers(0, n))]
    crit.update(tier=2, region=str(rng.choice(list(HIGH_RISK_REGIONS))),
                on_time_rate=round(float(rng.uniform(0.55, 0.66)), 3),
                lead_time_cov=round(float(rng.uniform(0.55, 0.8)), 2),
                annual_spend_musd=round(float(rng.uniform(3.5, 6.0)), 2),
                single_source=True)
    watch = suppliers[int(rng.integers(0, n))]
    if watch is not crit:
        watch.update(on_time_rate=round(float(rng.uniform(0.72, 0.8)), 3),
                     annual_spend_musd=round(float(rng.uniform(4.0, 6.0)), 2))

    for s in suppliers:
        s["risk_score"] = round(_risk_score(s), 1)
    suppliers.sort(key=lambda s: s["risk_score"], reverse=True)

    total_spend = round(sum(s["annual_spend_musd"] for s in suppliers), 2)
    late = [s for s in suppliers if s["on_time_rate"] < 0.85]
    # rough $ exposure: spend tied up in single-sourced or chronically-late suppliers
    exposure = round(sum(s["annual_spend_musd"] for s in suppliers
                         if s["single_source"] or s["on_time_rate"] < 0.8), 2)
    summary = {
        "suppliers": n,
        "tier2_count": sum(1 for s in suppliers if s["tier"] == 2),
        "single_source_count": sum(1 for s in suppliers if s["single_source"]),
        "high_risk_region_count": sum(1 for s in suppliers if s["region"] in HIGH_RISK_REGIONS),
        "avg_on_time_pct": round(100 * float(np.mean([s["on_time_rate"] for s in suppliers])), 1),
        "chronically_late_count": len(late),
        "total_annual_spend_musd": total_spend,
        "at_risk_spend_musd": exposure,
        "top_risk_supplier": suppliers[0]["supplier"],
    }
    return {"seed": seed, "n": n, "suppliers": suppliers, "summary": summary}


def dataset_to_text(ds: dict) -> str:
    """Compact markdown rendering of the dataset for the LLM to analyse."""
    s = ds["summary"]
    head = (
        f"SUPPLIER DATASET (seed {ds['seed']}, {s['suppliers']} suppliers)\n"
        f"Portfolio: ${s['total_annual_spend_musd']}M/yr total spend · "
        f"avg on-time {s['avg_on_time_pct']}% · {s['tier2_count']} Tier-2 · "
        f"{s['single_source_count']} single-sourced · "
        f"{s['high_risk_region_count']} in high-risk regions · "
        f"${s['at_risk_spend_musd']}M spend at risk.\n\n"
        "| Supplier | Tier | Region | Component | On-time% | Lead(d) | Lead CoV | Spend $M | Single-src | Risk |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = "\n".join(
        f"| {x['supplier']} | T{x['tier']} | {x['region']} | {x['component']} | "
        f"{round(x['on_time_rate']*100,1)} | {x['avg_lead_time_days']} | {x['lead_time_cov']} | "
        f"{x['annual_spend_musd']} | {'YES' if x['single_source'] else 'no'} | {x['risk_score']} |"
        for x in ds["suppliers"]
    )
    return head + rows
