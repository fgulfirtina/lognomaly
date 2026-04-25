"""
LogNomaly — /api/retrain endpoint (Continuous Learning Loop)

Supports 3 correction types that arrive via AnalystFeedback.ProposedLabel:
  • False Positive   : PredictedClass=threat, ProposedLabel="Normal"
  • False Negative   : PredictedClass="Normal", ProposedLabel=threat
  • Misclassification: PredictedClass=X, ProposedLabel=Y (both threats)
"""

import os, shutil, logging, datetime
import numpy as np
import pandas as pd
import joblib
from flask import request, jsonify
from scipy.sparse import hstack, csr_matrix
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

logger = logging.getLogger("retrain")

# ── Helpers  ────────────

def _backup_models(model_dir: str, prefix: str) -> str:
    """
    Copies existing .joblib files to a versioned backup folder.
    Returns the backup directory path.
    """
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(model_dir, "backups", f"{prefix or 'bgl'}_{ts}")
    os.makedirs(backup_dir, exist_ok=True)

    for fname in os.listdir(model_dir):
        if fname.endswith(".joblib") and fname.startswith(prefix):
            src = os.path.join(model_dir, fname)
            dst = os.path.join(backup_dir, fname)
            shutil.copy2(src, dst)
            logger.info("Backed up: %s → %s", fname, backup_dir)

    return backup_dir


def _build_correction_df(corrections: list) -> pd.DataFrame:
    """
    Converts the JSON corrections payload from C# into a DataFrame
    that mirrors the training schema.

    Each correction dict has:
      raw_log, predicted_class, proposed_label, analyst_notes
    """
    records = []
    for c in corrections:
        raw      = c.get("rawLog") or c.get("raw_log", "")
        label    = c.get("proposedLabel") or c.get("proposed_label", "Normal")
        level    = "INFO"  # analyst corrections rarely carry log-level metadata

        # Detect dataset type from raw log format (same heuristic as app.py)
        if raw.startswith(tuple("0123456789")) and "dfs." in raw:
            dataset_type = "HDFS"
        elif raw.startswith(tuple("0123456789")) and len(raw) > 20 and raw[6] == " ":
            dataset_type = "HDFS"
        else:
            dataset_type = "BGL"

        from app import clean_log, extract_hour  # local import to avoid circular deps
        hour    = extract_hour(raw, dataset_type)
        message = clean_log(raw)

        records.append({
            "level":   level,
            "message": message,
            "label":   label,
            "hour":    hour,
            "source":  "analyst_correction"
        })

    return pd.DataFrame(records)


def _retrain_bundle(bundle, extra_df: pd.DataFrame, base_sample: int = 2000):
    """
    Retrains the Isolation Forest and Random Forest in `bundle` by mixing:
      • All analyst corrections (full weight)
      • A random sample of the original CSV baseline (to preserve prior knowledge)

    Returns updated (iso, rf) models.
    """
    from app import MODEL_DIR, UPLOAD_DIR

    # ── 1. Load baseline CSV (if it exists) ──────────────────────────
    csv_name = "hdfs_train_ready.csv" if bundle.dataset_type == "HDFS" else "bgl_train_ready.csv"
    data_dir = os.path.join(os.path.dirname(MODEL_DIR), "data")
    csv_path = os.path.join(data_dir, csv_name)

    if os.path.exists(csv_path):
        base_df = pd.read_csv(csv_path).sample(
            n=min(base_sample, len(pd.read_csv(csv_path))),
            random_state=42
        )
        # Ensure schema compatibility
        for col in ["level", "message", "label", "hour"]:
            if col not in base_df.columns:
                base_df[col] = "INFO" if col == "level" else ("Normal" if col == "label" else -1)
        base_df = base_df[["level", "message", "label", "hour"]]
        combined = pd.concat([base_df, extra_df[["level", "message", "label", "hour"]]], ignore_index=True)
    else:
        logger.warning("No baseline CSV found at %s — training on corrections only.", csv_path)
        combined = extra_df[["level", "message", "label", "hour"]].copy()

    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)
    logger.info("Combined training set: %d rows | corrections: %d", len(combined), len(extra_df))

    # ── 2. Vectorise (reuse fitted tfidf + le from bundle) ────────────
    LEVEL_ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "UNKNOWN"]
    safe_levels  = combined["level"].apply(lambda x: x if x in bundle.le.classes_ else "UNKNOWN")
    level_enc    = bundle.le.transform(safe_levels).reshape(-1, 1)
    hours_norm   = combined["hour"].apply(lambda x: (x / 23.0) if x != -1 else 0.5).values.reshape(-1, 1)
    tfidf_mat    = bundle.tfidf.transform(combined["message"].fillna(""))
    X = hstack([csr_matrix(np.hstack([level_enc, hours_norm])), tfidf_mat]).toarray()

    y = combined["label"].values

    # ── 3. Handle rare classes ────────────────────────────────────────
    counts = pd.Series(y).value_counts()
    rare   = counts[counts < 2].index.tolist()
    if rare:
        y = np.where(np.isin(y, rare), "UnknownAnomaly", y)

    # ── 4. Retrain Isolation Forest ───────────────────────────────────
    anomaly_ratio  = float((pd.Series(y) != "Normal").mean())
    contamination  = float(np.clip(anomaly_ratio, 0.01, 0.49))
    iso = IsolationForest(
        contamination=contamination, n_estimators=200,
        random_state=42, n_jobs=-1
    )
    iso.fit(X)

    # ── 5. Retrain Random Forest ──────────────────────────────────────
    use_stratify = pd.Series(y).value_counts().min() >= 2
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42,
        stratify=y if use_stratify else None
    )
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=15,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    rf.fit(X_tr, y_tr)

    f1 = f1_score(y_te, rf.predict(X_te), average="weighted", zero_division=0)
    logger.info("Retrained %s — RF F1: %.3f | iso contamination: %.3f",
                bundle.dataset_type, f1, contamination)

    return iso, rf, float(f1)


# ── Flask Endpoint ────────────────────────────────────────────────────

def register_retrain_endpoint(app, bundles, MODEL_DIR):
    """
    Call this in app.py after creating the Flask app:

        from retrain_endpoint import register_retrain_endpoint
        register_retrain_endpoint(app, bundles, MODEL_DIR)
    """

    @app.post("/api/retrain")
    def retrain():
        body        = request.get_json(silent=True) or {}
        corrections = body.get("corrections", [])
        total       = body.get("total_count", len(corrections))

        if not corrections:
            return jsonify({"error": "No corrections provided."}), 400

        logger.info("Retrain triggered with %d corrections.", total)

        # ── Group by dataset type ─────────────────────────────────────
        bgl_corrections  = []
        hdfs_corrections = []

        for c in corrections:
            raw = c.get("rawLog") or c.get("raw_log", "")
            if (raw.startswith(tuple("0123456789")) and "dfs." in raw) or "blk_" in raw:
                hdfs_corrections.append(c)
            else:
                bgl_corrections.append(c)

        results = {}

        for dataset_type, corr_list in [("BGL", bgl_corrections), ("HDFS", hdfs_corrections)]:
            if not corr_list:
                continue

            bundle = bundles.get(dataset_type)
            if not bundle or not bundle.loaded:
                logger.warning("Bundle %s not loaded — skipping.", dataset_type)
                results[dataset_type] = {"skipped": True, "reason": "model not loaded"}
                continue

            try:
                # 1. Backup existing models
                prefix     = bundle.prefix
                backup_dir = _backup_models(MODEL_DIR, prefix)

                # 2. Build correction DataFrame
                corr_df = _build_correction_df(corr_list)

                # 3. Retrain
                iso, rf, f1 = _retrain_bundle(bundle, corr_df)

                # 4. Save new models (overwrites the live ones)
                joblib.dump(iso, os.path.join(MODEL_DIR, f"{prefix}iso_forest.joblib"))
                joblib.dump(rf,  os.path.join(MODEL_DIR, f"{prefix}rf_classifier.joblib"))

                # 5. Hot-reload into the running bundle
                bundle.iso    = iso
                bundle.rf     = rf
                bundle.loaded = True

                # 6. Update XAI explainer if available
                try:
                    from models.xai_explainer import XAIExplainer
                    bundle.explainer = XAIExplainer(rf, bundle.feature_names)
                except Exception:
                    pass

                results[dataset_type] = {
                    "success":          True,
                    "corrections_used": len(corr_list),
                    "new_f1_score":     round(f1, 4),
                    "backup_dir":       backup_dir
                }
                logger.info("%s models updated and hot-reloaded.", dataset_type)

            except Exception as e:
                logger.exception("Retrain failed for %s", dataset_type)
                results[dataset_type] = {"success": False, "error": str(e)}

        overall_success = any(v.get("success") for v in results.values())

        return jsonify({
            "status":      "ok" if overall_success else "partial_failure",
            "total_input": total,
            "results":     results,
            "retrained_at": datetime.datetime.utcnow().isoformat()
        }), 200 if overall_success else 500