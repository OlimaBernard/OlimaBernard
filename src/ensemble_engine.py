from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class EnsemblePackage:
    models: dict
    weights: dict
    classes: list[str]
    feature_cols: list[str]
    validation: dict
    approved: bool
    metadata: dict


def normalize_weights(scores: dict[str, float]) -> dict[str, float]:
    positive = {k: max(float(v), 0.0001) for k, v in scores.items()}
    total = sum(positive.values()) or 1.0
    return {k: v / total for k, v in positive.items()}


def ensemble_predict_proba(package: EnsemblePackage, X: pd.DataFrame) -> pd.DataFrame:
    classes = package.classes
    final = np.zeros((len(X), len(classes)))
    for name, model in package.models.items():
        if name not in package.weights:
            continue
        probs = model.predict_proba(X[package.feature_cols])
        aligned = np.zeros_like(final)
        for i, cls in enumerate(model.classes_):
            if cls in classes:
                aligned[:, classes.index(cls)] = probs[:, i]
        final += aligned * package.weights[name]
    return pd.DataFrame(final, columns=classes, index=X.index)


def final_bias_from_probs(probs: pd.Series, min_conf: float) -> tuple[str, float]:
    best_label = str(probs.idxmax())
    confidence = float(probs.max())
    if best_label in {"Bullish", "Bearish"} and confidence < min_conf:
        return "Neutral", confidence
    return best_label, confidence
