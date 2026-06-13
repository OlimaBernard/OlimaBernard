from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, classification_report


@dataclass
class ValidationResult:
    accuracy: float
    precision_by_class: Dict[str, float]
    approved: bool
    min_required_accuracy: float
    report: str


def validate_predictions(y_true, y_pred, timeframe_name: str, settings: dict) -> ValidationResult:
    acc = float(accuracy_score(y_true, y_pred)) if len(y_true) else 0.0
    labels = ["Bullish", "Bearish", "Neutral"]
    prec_arr = precision_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    precision_by_class = {label: float(val) for label, val in zip(labels, prec_arr)}
    min_acc = settings.get("validation", {}).get("daily_min_accuracy" if timeframe_name == "daily" else "weekly_min_accuracy", 0.55)
    approved = acc >= float(min_acc)
    report = classification_report(y_true, y_pred, labels=labels, zero_division=0)
    return ValidationResult(acc, precision_by_class, approved, float(min_acc), report)
