from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover
    LGBMClassifier = None

from .ensemble_engine import EnsemblePackage, normalize_weights
from .feature_engineering import feature_columns
from .utils import read_json, root_path, safe_symbol_name, timeframe_name, write_json
from .validator import validate_predictions


class XGBLabelWrapper(BaseEstimator, ClassifierMixin):
    """Wraps XGBClassifier so it accepts string class labels.

    Modern XGBoost (>=1.6) requires integer-encoded targets for multiclass
    classification and will reject string labels such as
    ['Bearish', 'Bullish'] with:

        Invalid classes inferred from unique values of `y`.
        Expected: [0 1 2], got ['Bearish' 'Bullish']

    This wrapper encodes labels to integers before fitting and decodes
    predictions back to strings, and exposes ``classes_`` as the original
    string labels so the ensemble and validator keep working unchanged.

    NOTE: it must be defined at module level so joblib can unpickle any
    EnsemblePackage that contains a fitted instance.
    """

    def __init__(self, estimator):
        self.estimator = estimator

    def fit(self, X, y):
        self._le = LabelEncoder()
        y_enc = self._le.fit_transform(y)
        self.estimator.fit(X, y_enc)
        # LabelEncoder sorts alphabetically: Bearish->0, Bullish->1->2.
        # predict_proba columns follow the same 0..n order, so they align with
        # classes_ (standard sklearn convention).
        self.classes_ = self._le.classes_
        return self

    def predict(self, X):
        pred = self.estimator.predict(X)
        return self._le.inverse_transform(np.asarray(pred).astype(int))

    def predict_proba(self, X):
        return self.estimator.predict_proba(X)


def _make_models(random_state: int = 42) -> dict:
    models = {
        "logistic": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]),
        "random_forest": RandomForestClassifier(
            n_estimators=350,
            max_depth=8,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=random_state,
            n_jobs=-1,
        ),
    }
    if XGBClassifier is not None:
        models["xgboost"] = XGBLabelWrapper(XGBClassifier(
            n_estimators=250,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="mlogloss",
            random_state=random_state,
        ))
    elif LGBMClassifier is not None:
        # LightGBM handles string labels internally, so no wrapper is needed.
        models["lightgbm"] = LGBMClassifier(
            n_estimators=250,
            max_depth=4,
            learning_rate=0.05,
            random_state=random_state,
        )
    return models


def train_ensemble(features: pd.DataFrame, symbol: str, timeframe: str, group: str, settings: dict) -> EnsemblePackage:
    tf_name = timeframe_name(timeframe)
    df = features.dropna(subset=["target"]).copy()
    cols = feature_columns(df)
    df = df[df["target"].isin(["Bullish", "Bearish"])]

    if len(df) < 50:
        raise ValueError(f"Insufficient rows to train {symbol} {timeframe}: {len(df)}")

    split = int(len(df) * (1 - float(settings.get("validation", {}).get("test_size", 0.25))))
    train, test = df.iloc[:split].copy(), df.iloc[split:].copy()

    # --- Feature cleaning (leak-free) -------------------------------------
    # Drop features that are entirely NaN within the TRAINING window. With an
    # empty news feed (ForexFactory rows=0) every news-derived column is NaN,
    # and a blanket fillna(0.0) would feed dead constant columns to the models.
    usable_cols = [c for c in cols if not train[c].isna().all()]
    dropped = [c for c in cols if c not in usable_cols]
    if dropped:
        print(f"Dropping {len(dropped)} all-NaN feature(s) for {symbol} {timeframe}: {dropped}")
    cols = usable_cols
    if not cols:
        raise ValueError(f"No usable features for {symbol} {timeframe} (all NaN)")

    # Impute remaining gaps with TRAIN medians (computed on train rows only to
    # avoid lookahead leakage). Fall back to 0.0 only where a median is undefined.
    medians = train[cols].median(numeric_only=True).fillna(0.0)
    train[cols] = train[cols].fillna(medians)
    test[cols] = test[cols].fillna(medians)

    X_train, y_train = train[cols], train["target"]
    X_test, y_test = test[cols], test["target"]
    # ----------------------------------------------------------------------

    fitted = {}
    scores = {}
    model_reports = {}
    for name, model in _make_models().items():
        try:
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
            res = validate_predictions(y_test, pred, tf_name, settings)
            fitted[name] = model
            scores[name] = max(res.accuracy, 0.0001)
            model_reports[name] = {
                "accuracy": res.accuracy,
                "precision_by_class": res.precision_by_class,
                "approved": res.approved,
                "min_required_accuracy": res.min_required_accuracy,
            }
        except Exception as e:
            print(f"Model {name} failed for {symbol} {timeframe}: {e}")

    if not fitted:
        raise RuntimeError(f"No model could be trained for {symbol} {timeframe}")

    weights = normalize_weights(scores)

    # Ensemble validation
    from .ensemble_engine import ensemble_predict_proba
    temp_pkg = EnsemblePackage(
        models=fitted,
        weights=weights,
        classes=["Bullish", "Bearish"],
        feature_cols=cols,
        validation={},
        approved=False,
        metadata={},
    )
    proba = ensemble_predict_proba(temp_pkg, X_test)
    ens_pred = proba.idxmax(axis=1)
    ens_res = validate_predictions(y_test, ens_pred, tf_name, settings)

    metadata = {
        "symbol": symbol,
        "group": group,
        "timeframe": timeframe,
        "timeframe_name": tf_name,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "rows": len(df),
        "train_rows": len(train),
        "test_rows": len(test),
        "last_training_candle": str(df["Date"].iloc[-1]),
        # Persist imputation values so inference can fill gaps identically.
        "feature_medians": medians.to_dict(),
        "dropped_features": dropped,
    }
    return EnsemblePackage(
        models=fitted,
        weights=weights,
        classes=["Bullish", "Bearish"],
        feature_cols=cols,
        validation={
            "ensemble_accuracy": ens_res.accuracy,
            "ensemble_precision_by_class": ens_res.precision_by_class,
            "approved": ens_res.approved,
            "min_required_accuracy": ens_res.min_required_accuracy,
            "model_reports": model_reports,
        },
        approved=ens_res.approved,
        metadata=metadata,
    )


def next_version(symbol: str, timeframe_name_: str, registry: dict) -> str:
    current = registry.get(symbol, {}).get(timeframe_name_, {}).get("version")
    if current is None:
        return "v1.0"
    try:
        n = float(str(current).replace("v", "")) + 0.1
        return f"v{n:.1f}"
    except Exception:
        return "v1.0"


def save_model(package: EnsemblePackage, settings: dict) -> Path:
    registry_path = root_path(settings.get("models", {}).get("registry_file", "models/model_registry.json"))
    registry = read_json(registry_path, {})
    symbol = safe_symbol_name(package.metadata["symbol"])
    tf_name = package.metadata["timeframe_name"]
    version = next_version(symbol, tf_name, registry)
    package.metadata["version"] = version
    fname = f"{symbol}_{tf_name}_{version}.pkl"
    path = root_path("models", fname)
    joblib.dump(package, path)

    registry.setdefault(symbol, {})[tf_name] = {
        "active_file": fname,
        "version": version,
        "approved": package.approved,
        "updated_at": package.metadata["trained_at"],
        "last_training_candle": package.metadata["last_training_candle"],
    }
    write_json(registry_path, registry)
    return path


def load_active_model(symbol: str, timeframe: str, settings: dict) -> EnsemblePackage | None:
    registry_path = root_path(settings.get("models", {}).get("registry_file", "models/model_registry.json"))
    registry = read_json(registry_path, {})
    sym = safe_symbol_name(symbol)
    tf_name = timeframe_name(timeframe)
    rec = registry.get(sym, {}).get(tf_name)
    if not rec:
        return None
    path = root_path("models", rec["active_file"])
    if not path.exists():
        return None
    return joblib.load(path)