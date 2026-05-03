"""Per-layer logistic-regression probes on residual-stream activations.

Trains one sklearn LogisticRegression per layer on contrastive labels
(honest=0 / deceptive=1 or similar binary split). Reports AUC/acc/coef_norm
on a stratified 20% holdout.

No per-layer standardization is applied in the MVP because residual-stream
activations from the same model family are expected to be roughly comparable
within a layer; revisit this if cross-model or mixed-normalization probes enter
the scope.
"""

import json
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split


def _both_classes(values: np.ndarray) -> bool:
    return set(values.astype(int).tolist()) == {0, 1}


def _choose_split(
    labels: np.ndarray,
    groups: np.ndarray | None,
    test_size: float,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray, str, dict]:
    """Choose row-wise or group-wise train/test indices.

    Grouped splitting keeps duplicate prompts/templates from appearing in both
    train and test. If grouped splitting is requested but cannot produce both
    classes on both sides, fail loudly instead of reporting an inflated probe AUC.
    """
    indices = np.arange(labels.shape[0])
    if groups is None:
        train_idx, test_idx = train_test_split(
            indices, test_size=test_size, stratify=labels, random_state=random_state
        )
        return (
            train_idx,
            test_idx,
            "row_stratified",
            {
                "train_groups": None,
                "test_groups": None,
            },
        )

    groups = np.asarray(groups)
    unique_groups = np.unique(groups)
    if unique_groups.shape[0] == labels.shape[0]:
        train_idx, test_idx = train_test_split(
            indices, test_size=test_size, stratify=labels, random_state=random_state
        )
        return (
            train_idx,
            test_idx,
            "row_stratified_no_duplicate_groups",
            {
                "train_groups": int(np.unique(groups[train_idx]).shape[0]),
                "test_groups": int(np.unique(groups[test_idx]).shape[0]),
            },
        )

    splitter = GroupShuffleSplit(
        n_splits=200, test_size=test_size, random_state=random_state
    )
    for train_idx, test_idx in splitter.split(indices, labels, groups):
        if _both_classes(labels[train_idx]) and _both_classes(labels[test_idx]):
            return (
                train_idx,
                test_idx,
                "group_shuffle",
                {
                    "train_groups": int(np.unique(groups[train_idx]).shape[0]),
                    "test_groups": int(np.unique(groups[test_idx]).shape[0]),
                },
            )

    raise ValueError(
        "Could not create a grouped train/test split with both classes on both "
        f"sides. rows={labels.shape[0]}, groups={unique_groups.shape[0]}, "
        f"pos={int(labels.sum())}, neg={int((labels == 0).sum())}. "
        "Add more prompt groups or use a row-wise smoke run only if the result "
        "will not be used as evidence."
    )


def train_probes(
    activations: np.ndarray,
    labels: np.ndarray,
    groups: np.ndarray | None = None,
    random_state: int = 42,
    test_size: float = 0.2,
    max_iter: int = 2000,
) -> dict:
    """Fit a per-layer logistic regression, return metrics keyed by layer index.

    activations: (N, L, H) — N prompts, L layers, H hidden dim.
    labels: (N,) binary integer labels.
    Returns: {layer_idx: {"auc": float, "acc": float, "coef_norm": float}}.
    """
    assert activations.ndim == 3, f"expected (N,L,H), got {activations.shape}"
    assert (
        activations.shape[0] == labels.shape[0]
    ), "N mismatch between activations and labels"
    N, L, H = activations.shape
    print(
        f"[train] N={N} layers={L} hidden={H} pos={int(labels.sum())} neg={int((labels == 0).sum())}"
    )
    train_idx, test_idx, split_strategy, split_meta = _choose_split(
        labels=labels,
        groups=groups,
        test_size=test_size,
        random_state=random_state,
    )
    print(f"[train] split={split_strategy} train={len(train_idx)} test={len(test_idx)}")

    results: dict[int, dict] = {}
    for layer_idx in range(L):
        X = activations[:, layer_idx, :]
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = labels[train_idx], labels[test_idx]
        clf = LogisticRegression(
            class_weight="balanced",
            max_iter=max_iter,
            random_state=random_state,
            solver="liblinear",
        )
        clf.fit(X_tr, y_tr)
        proba = clf.predict_proba(X_te)[:, 1]
        preds = clf.predict(X_te)
        try:
            auc = float(roc_auc_score(y_te, proba))
        except ValueError:
            # single-class holdout — shouldn't happen with stratify, defensive
            auc = float("nan")
        acc = float(accuracy_score(y_te, preds))
        coef_norm = float(np.linalg.norm(clf.coef_))
        results[layer_idx] = {
            "auc": auc,
            "acc": acc,
            "coef_norm": coef_norm,
            "split_strategy": split_strategy,
            "n_train": int(len(train_idx)),
            "n_test": int(len(test_idx)),
            **split_meta,
        }
    return results


def save_results(
    results: dict, out_path: Path, stage: str, run_id: Optional[str] = None
) -> None:
    """Dump probe results to JSON."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # int keys -> str for JSON
    serial = {
        "stage": stage,
        "run_id": run_id,
        "per_layer": {str(k): v for k, v in results.items()},
    }
    with open(out_path, "w") as f:
        json.dump(serial, f, indent=2)
    print(f"[train] wrote {out_path}")


def load_results(path: Path) -> dict:
    """Inverse of save_results. Returns {layer_idx(int): {...}}."""
    path = Path(path)
    raw = json.loads(path.read_text())
    return {int(k): v for k, v in raw["per_layer"].items()}
