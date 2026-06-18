"""
Late-delivery risk model (LightGBM, native API — no scikit-learn).

Demonstrates a real ML pipeline: synthesise a labelled history of past
deliveries, train a gradient-boosted classifier to predict late delivery from
supplier features, report holdout AUC + feature importances, and score the
currently loaded suppliers.

NOTE: the training history is SIMULATED (we have no real delivery logs), so the
model is illustrative — but the pipeline (features → train → validate → predict →
explain) is exactly what you'd run on real data.
"""

import numpy as np

FEATURES = ["on_time_rate", "lead_time_cov", "annual_spend_musd",
            "single_source", "high_risk_region"]
_HIGH_RISK = {"TW", "Taiwan", "VN", "Vietnam", "IN", "India", "CN", "China"}


def _features(sup: dict) -> list:
    return [
        float(sup.get("on_time_rate") or 0.9),
        float(sup.get("lead_time_cov") or 0.2),
        float(sup.get("annual_spend_musd") or 1.0),
        1.0 if sup.get("single_source") else 0.0,
        1.0 if str(sup.get("region", "")) in _HIGH_RISK else 0.0,
    ]


def _synth_history(rng, n=1500):
    """Synthesise labelled past deliveries: features → was_late (0/1)."""
    on_time = np.clip(rng.normal(0.88, 0.1, n), 0.4, 0.999)
    cov = np.clip(rng.normal(0.25, 0.12, n), 0.02, 0.9)
    spend = rng.uniform(0.2, 6.0, n)
    single = (rng.random(n) < 0.3).astype(float)
    hirisk = (rng.random(n) < 0.35).astype(float)
    X = np.column_stack([on_time, cov, spend, single, hirisk])
    # latent lateness driven by the features (+ noise) → probability → label
    logit = (-2.0 + (1 - on_time) * 5 + cov * 2.5 + single * 0.8 + hirisk * 1.1
             + spend * 0.05 + rng.normal(0, 0.4, n))
    p = 1 / (1 + np.exp(-logit))
    y = (rng.random(n) < p).astype(int)
    return X, y


def _auc(y, p):
    """Rank-based AUC (no sklearn)."""
    y = np.asarray(y); p = np.asarray(p)
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(p)
    ranks = np.empty(len(p)); ranks[order] = np.arange(1, len(p) + 1)
    return float((ranks[y == 1].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def run_forecast(suppliers: list, seed: int | None = None) -> dict | None:
    """Train on simulated history, score the loaded suppliers. None if no suppliers."""
    if not suppliers:
        return None
    try:
        import lightgbm as lgb
    except Exception:
        return None
    rng = np.random.default_rng((seed or 0) + 11)
    X, y = _synth_history(rng)
    cut = int(len(X) * 0.8)
    dtrain = lgb.Dataset(X[:cut], y[:cut], feature_name=FEATURES)
    dval = lgb.Dataset(X[cut:], y[cut:], reference=dtrain)
    params = {"objective": "binary", "metric": "auc", "verbosity": -1,
              "num_leaves": 16, "learning_rate": 0.08, "feature_pre_filter": False}
    bst = lgb.train(params, dtrain, num_boost_round=120, valid_sets=[dval])
    auc = _auc(y[cut:], bst.predict(X[cut:]))

    Xc = np.array([_features(s) for s in suppliers])
    probs = bst.predict(Xc)
    preds = sorted(
        [{"supplier": s.get("supplier", "—"), "late_risk_pct": round(float(p) * 100, 1)}
         for s, p in zip(suppliers, probs)],
        key=lambda d: d["late_risk_pct"], reverse=True)

    gain = bst.feature_importance(importance_type="gain")
    tot = float(gain.sum()) or 1.0
    importances = sorted(
        [{"feature": f, "importance_pct": round(100 * float(g) / tot, 1)}
         for f, g in zip(FEATURES, gain)],
        key=lambda d: d["importance_pct"], reverse=True)

    return {
        "model": "LightGBM (binary late-delivery)", "simulated_training": True,
        "holdout_auc": round(auc, 3), "train_rows": cut,
        "predictions": preds,
        "feature_importance": importances,
        "predicted_late_count": sum(1 for p in preds if p["late_risk_pct"] >= 50),
    }


def forecast_to_text(fc: dict) -> str:
    if not fc:
        return ""
    top = ", ".join(f"{p['supplier']} {p['late_risk_pct']}%" for p in fc["predictions"][:5])
    imp = ", ".join(f"{i['feature']} {i['importance_pct']}%" for i in fc["feature_importance"])
    return (f"ML LATE-DELIVERY RISK MODEL ({fc['model']}, trained on simulated history, "
            f"holdout AUC {fc['holdout_auc']}): predicted late-risk per supplier — {top}. "
            f"Feature importance: {imp}. {fc['predicted_late_count']} suppliers ≥50% late risk.")
