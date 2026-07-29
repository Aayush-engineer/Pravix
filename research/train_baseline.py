"""
Pravix — Phase 0 baseline model training/evaluation.

Loads the PR dataset collected by pull_pr_data.py, trains the simplest
model that could plausibly work (logistic regression on structural
features), and reports honest accuracy/AUC/precision-at-top-20% —
the numbers that go into research/findings.md.

Deliberately NOT trying to beat the published "Circuit Breaker" paper's
0.96 AUC on the first attempt. The goal here is: does a simple model
show ANY meaningful signal above random guessing? If yes, iterate.
If no, that's important information now, not after building a tool
on top of it.

Usage:
    python train_baseline.py
    python train_baseline.py --data ../data/training/pr_dataset_raw.csv
"""

import argparse
import json
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "diff_size",
    "changed_files",
    "commits",
    "comments",
    "review_comments",
    "has_plan",
    "body_length",
]
# force_pushed is included only if present and not all-null (depends on
# whether pull_pr_data.py was run with --include-force-push)
OPTIONAL_FEATURE_COLUMNS = ["force_pushed"]

TARGET_COLUMN = "merged"
MIN_ROWS_WARNING = 200


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Only keep closed PRs — "still open" isn't a resolved label yet
    df = df[df["state"] == "closed"].copy()
    return df


def build_features(df: pd.DataFrame):
    columns = FEATURE_COLUMNS.copy()

    for col in OPTIONAL_FEATURE_COLUMNS:
        if col in df.columns and df[col].notna().any():
            df[col] = df[col].fillna(False).astype(int)
            columns.append(col)

    df["has_plan"] = df["has_plan"].astype(int)
    df["body_length"] = df["body_length"].fillna(0)

    # One-hot encode author (agent identity) — a known strong signal per the research
    author_dummies = pd.get_dummies(df["author"], prefix="agent")
    X = pd.concat([df[columns], author_dummies], axis=1)
    y = df[TARGET_COLUMN].astype(int)

    return X, y, columns


def precision_at_top_k(y_true, y_scores, k_fraction=0.2) -> float:
    """Of the top k% highest-risk-predicted PRs (lowest predicted merge probability),
    what fraction were actually not merged? Mirrors how the 'Circuit Breaker' paper
    reports usefulness — catching the worst offenders cheaply, not perfect accuracy."""
    n = len(y_scores)
    k = max(1, int(n * k_fraction))
    # lowest predicted merge probability = highest predicted risk
    risk_order = np.argsort(y_scores)[:k]
    flagged_true = y_true.iloc[risk_order] if hasattr(y_true, "iloc") else y_true[risk_order]
    return float((flagged_true == 0).mean())  # fraction correctly flagged as "did not merge"


def main():
    parser = argparse.ArgumentParser(description="Train Pravix Phase 0 baseline model.")
    parser.add_argument("--data", default="../data/training/pr_dataset_raw.csv")
    parser.add_argument("--output", default="../research/findings_raw.json",
                         help="Where to save the raw metrics JSON, used to write findings.md")
    args = parser.parse_args()

    df = load_data(args.data)

    if len(df) < MIN_ROWS_WARNING:
        print(f"WARNING: only {len(df)} closed PRs available. Results below "
              f"{MIN_ROWS_WARNING} rows are not reliable — treat as a smoke test, "
              f"not a real finding. Keep collecting data.")

    if df[TARGET_COLUMN].nunique() < 2:
        sys.exit("All PRs in the dataset have the same outcome (all merged or all "
                  "not-merged) — cannot train a classifier. Collect a more varied sample.")

    X, y, feature_names = build_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    y_scores = model.predict_proba(X_test_scaled)[:, 1]  # P(merged)

    metrics = {
        "n_total": len(df),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "merge_rate": float(y.mean()),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "auc": float(roc_auc_score(y_test, y_scores)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "precision_at_top_20pct_risk": precision_at_top_k(y_test.reset_index(drop=True),
                                                            y_scores, 0.2),
        "feature_importance": dict(zip(X.columns, model.coef_[0].round(4).tolist())),
    }

    print(json.dumps(metrics, indent=2))

    with open(args.output, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved raw metrics to {args.output} — use these to write research/findings.md")

    print("\nReminder: compare metrics['auc'] against the published Circuit Breaker "
          "paper's 0.96. A lower number on your smaller, self-collected dataset is "
          "expected and fine — report it honestly either way.")


if __name__ == "__main__":
    main()