"""Loads and validates the metric registry."""
from __future__ import annotations

import yaml

from . import config

REQUIRED = ["id", "display_name", "status_kind", "source", "update_cadence",
            "adjustment_pipeline", "known_confounds", "chart_type", "caveat_line"]
REQUIRED_SOURCE = ["name", "api", "endpoint", "series_id"]
REQUIRED_LANDMARK = ["id", "display_name", "metric", "threshold", "direction",
                     "method", "caveat_line"]


def load() -> dict:
    reg = yaml.safe_load(config.REGISTRY.read_text())
    metrics = {}
    for m in reg["metrics"]:
        missing = [k for k in REQUIRED if k not in m]
        missing += [f"source.{k}" for k in REQUIRED_SOURCE if k not in m.get("source", {})]
        if missing:
            raise ValueError(f"registry entry {m.get('id')} missing {missing}")
        metrics[m["id"]] = m
    landmarks = {}
    for lm in reg["landmarks"]:
        missing = [k for k in REQUIRED_LANDMARK if k not in lm]
        if missing:
            raise ValueError(f"landmark {lm.get('id')} missing {missing}")
        if lm["metric"] not in metrics:
            raise ValueError(f"landmark {lm['id']} references unknown metric")
        landmarks[lm["id"]] = lm
    return {"metrics": metrics, "landmarks": landmarks}


def require(reg: dict, metric_id: str) -> dict:
    if metric_id not in reg["metrics"]:
        raise KeyError(f"metric {metric_id} computed but not in registry")
    return reg["metrics"][metric_id]
