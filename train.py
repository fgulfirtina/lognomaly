import os, re, sys, logging
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score
from scipy.sparse import hstack, csr_matrix

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("bgl_train")

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "saved_models")
OUT_CSV   = os.path.join(DATA_DIR, "bgl_train_ready.csv")

BGL_PATH = None
for _name in ["BGL.log", "bgl2", "BGL_500k.log", "bgl.log"]:
    _p = os.path.join(DATA_DIR, _name)
    if os.path.exists(_p):
        BGL_PATH = _p
        break

MAX_LINES = 500_000

# =====================================================================
# 1. VERİ HAZIRLAMA
# =====================================================================
def prepare_data() -> pd.DataFrame:
    if BGL_PATH is None:
        sys.exit(
            "HATA: BGL.log bulunamadı!\n"
            f"Şu konuma koy: {os.path.join(DATA_DIR, 'BGL.log')}"
        )

    log.info("BGL dosyası: %s", BGL_PATH)
    log.info("Maksimum satır: %s", MAX_LINES or "Tümü")


    bgl_re = re.compile(
        r"^(-|[A-Z0-9_]+)"          # 1: flag  (- = normal, FATAL vs.)
        r"\s+\d+"                    # int timestamp — yoksay
        r"\s+\d{4}\.\d{2}\.\d{2}"   # tarih — yoksay
        r"\s+\S+"                    # node — yoksay
        r"\s+\S+"                    # datetime timestamp — yoksay
        r"\s+(\S+)"                  # 2: node2 (servis olarak kullan)
        r"\s+\S+"                    # type (RAS vs.) — yoksay
        r"\s+(\S+)"                  # 3: component (KERNEL vs.)
        r"\s+(\w+)"                  # 4: level (INFO, FATAL vs.)
        r"\s+(.+)$"                  # 5: mesaj
    )

    records = []
    skipped = 0
    total   = 0

    with open(BGL_PATH, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            if MAX_LINES and total >= MAX_LINES:
                break
            line = raw.strip()
            if not line:
                continue
            total += 1

            m = bgl_re.match(line)
            if not m:
                skipped += 1
                continue

            flag, node2, component, level, message = m.groups()
            label = _map_label(flag)
            level = _norm_level(level)

            records.append({
                "level":   level,
                "service": component,
                "message": message,
                "label":   label,
            })

            if len(records) % 100_000 == 0:
                log.info("  %d satır işlendi...", len(records))

    df = pd.DataFrame(records)

    log.info("Parse tamamlandı: %d kayıt, %d satır atlandı", len(df), skipped)
    log.info("Label dağılımı:\n%s", df["label"].value_counts().to_string())


    CLASS_LIMITS = {"Normal": 5, "SystemFailure": 200, "AppError": 50}
    parts = []
    for lbl, grp in df.groupby("label", sort=False):
        limit = CLASS_LIMITS.get(lbl, 50)
        parts.append(grp.groupby("message", sort=False).head(limit))
    df = (pd.concat(parts)
            .sample(frac=1, random_state=42)
            .reset_index(drop=True))
    log.info("Tekilleştirme sonrası: %d satır", len(df))
    log.info("Label dağılımı (son):\n%s", df["label"].value_counts().to_string())

    anomaly_ratio = (df["label"] != "Normal").mean()
    if anomaly_ratio < 0.01:
        log.warning("Anomali oranı çok düşük (%.2f%%) — model zayıf kalabilir!", anomaly_ratio * 100)

    df.to_csv(OUT_CSV, index=False)
    log.info("CSV kaydedildi: %s", OUT_CSV)
    return df


def _map_label(flag: str) -> str:
    flag = flag.strip()
    if flag == "-":
        return "Normal"
    flag_up = flag.upper()
    if "FATAL" in flag_up or "KERN" in flag_up:
        return "SystemFailure"
    if "APP" in flag_up:
        return "AppError"
    if "HARDWARE" in flag_up or "HW" in flag_up:
        return "HardwareFailure"
    return "UnknownAnomaly"


def _norm_level(level: str) -> str:
    MAP = {"WARN": "WARNING", "FATAL": "CRITICAL",
           "ERR": "ERROR", "SEVERE": "CRITICAL"}
    return MAP.get(level.upper(), level.upper())


# =====================================================================
# 2. FEATURE EXTRACTION
# =====================================================================
def extract_features(df: pd.DataFrame):
    LEVEL_ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "UNKNOWN"]

    le = LabelEncoder().fit(LEVEL_ORDER)
    safe_levels = df["level"].apply(lambda x: x if x in LEVEL_ORDER else "UNKNOWN")
    level_enc = le.transform(safe_levels).reshape(-1, 1)

    tfidf = TfidfVectorizer(max_features=150, sublinear_tf=True, ngram_range=(1, 2))
    tfidf_mat = tfidf.fit_transform(df["message"].fillna(""))

    time_delta = np.zeros((len(df), 1))

    X = hstack([csr_matrix(np.hstack([level_enc, time_delta])), tfidf_mat]).toarray()
    log.info("Feature matrix: %s", X.shape)
    return X, tfidf, le


# =====================================================================
# 3. MODEL EĞİTİMİ
# =====================================================================
def train(df: pd.DataFrame, X: np.ndarray):
    os.makedirs(MODEL_DIR, exist_ok=True)

    anomaly_ratio = float((df["label"] != "Normal").mean())
    contamination = float(np.clip(anomaly_ratio, 0.01, 0.49))
    log.info("Anomali oranı: %.3f → IF contamination: %.3f",
             anomaly_ratio, contamination)

    # ── Layer 2: Isolation Forest ─────────────────────────────────
    log.info("Isolation Forest eğitiliyor...")
    iso = IsolationForest(
        contamination=contamination,
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X)
    joblib.dump(iso, os.path.join(MODEL_DIR, "iso_forest.joblib"))
    log.info("  ✅ iso_forest.joblib kaydedildi.")

    # ── Layer 3: Random Forest ─────────────────────────────────────
    y = df["label"].values
    log.info("RF etiket dağılımı:\n%s", pd.Series(y).value_counts().to_string())

    counts = pd.Series(y).value_counts()
    rare   = counts[counts < 2].index.tolist()
    if rare:
        log.warning("Nadir sınıflar UnknownAnomaly'ye birleştirildi: %s", rare)
        y = np.where(np.isin(y, rare), "UnknownAnomaly", y)

    use_stratify = pd.Series(y).value_counts().min() >= 2
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42,
        stratify=y if use_stratify else None
    )

    log.info("Random Forest eğitiliyor... (bu biraz sürebilir)")
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_tr, y_tr)

    y_pred = rf.predict(X_te)
    f1     = f1_score(y_te, y_pred, average="weighted")
    log.info("Test F1 (weighted): %.3f", f1)
    if f1 < 0.80:
        log.warning("F1 < 0.80 — daha fazla veri veya hiperparametre ayarı gerekebilir.")
    log.info("\n%s", classification_report(y_te, y_pred, zero_division=0))

    joblib.dump(rf, os.path.join(MODEL_DIR, "rf_classifier.joblib"))
    log.info("  ✅ rf_classifier.joblib kaydedildi.")

    return iso, rf


# =====================================================================
# 4. FEATURE EXTRACTOR KAYDET
# =====================================================================
def save_extractor(tfidf, le):
    sys.path.insert(0, BASE_DIR)
    try:
        from utils.feature_extractor import FeatureExtractor
        ext = FeatureExtractor.__new__(FeatureExtractor)
        ext.tfidf             = tfidf
        ext.level_encoder     = le
        ext._is_fitted        = True
        ext.max_tfidf_features = 150
        ext.feature_names     = (["level_encoded", "time_delta_sec"]
                                  + tfidf.get_feature_names_out().tolist())
        joblib.dump(ext, os.path.join(MODEL_DIR, "feature_extractor.joblib"))
    except ImportError:
        obj = {"tfidf": tfidf, "level_encoder": le,
               "feature_names": (["level_encoded", "time_delta_sec"]
                                  + tfidf.get_feature_names_out().tolist())}
        joblib.dump(obj, os.path.join(MODEL_DIR, "feature_extractor.joblib"))
    log.info("  ✅ feature_extractor.joblib kaydedildi.")


# =====================================================================
# 5. HIZLI TEST
# =====================================================================
def quick_test(iso, rf, tfidf, le):
    log.info("\n── Hızlı Test ──────────────────────────────")

    RULES = [
        (re.compile(r"failed.*(login|password|auth)|too many attempt", re.I), "BruteForce",    1.0),
        (re.compile(r"fatal|kernel panic|machine check|uncorrectable",  re.I), "SystemFailure", 0.95),
        (re.compile(r"out of memory|oom|segmentation fault",            re.I), "SystemFailure", 0.90),
    ]

    test_logs = [
        ("INFO",    "instruction cache parity error corrected"),
        ("FATAL",   "kernel: EXT3-fs error (device sda3): ext3_find_entry"),
        ("WARNING", "ciod: failed to read message prefix on control stream"),
        ("INFO",    "BLOCK* NameSystem.addStoredBlock: blockMap updated"),
        ("ERROR",   "machine check: uncorrectable error in memory"),
        ("INFO",    "rts: kernel: fatal error in blade"),
    ]

    for lvl, msg in test_logs:
        rule_hit, risk, label = False, 0.0, "Normal"
        for pattern, threat, fixed_score in RULES:
            if pattern.search(msg):
                risk, label, rule_hit = fixed_score, threat, True
                break

        if not rule_hit:
            safe_lvl  = lvl if lvl in le.classes_ else "INFO"
            level_enc = le.transform([safe_lvl]).reshape(1, 1)
            td        = np.zeros((1, 1))
            x = hstack([csr_matrix(np.hstack([level_enc, td])),
                        tfidf.transform([msg])]).toarray()

            iso_score    = iso.decision_function(x)[0]
            anomaly_prob = float(np.clip(1.0 - (np.clip(iso_score, -0.5, 0.5) + 0.5), 0, 1))
            iso_pred     = iso.predict(x)[0]

            if iso_pred == 1:
                risk, label = anomaly_prob * 0.2, "Normal"
            else:
                probs   = rf.predict_proba(x)[0]
                label   = rf.classes_[np.argmax(probs)]
                rf_conf = float(np.max(probs))
                risk    = 0.4 * anomaly_prob + 0.6 * rf_conf

        icon = "🔴 HIGH  " if risk >= 0.8 else ("🟠 MEDIUM" if risk >= 0.5 else "🟢 LOW   ")
        log.info("  [%s %.2f]  %-18s %s", icon, risk, label, msg[:55])


# =====================================================================
# MAIN
# =====================================================================
if __name__ == "__main__":
    log.info("=" * 55)
    log.info("LogNomaly — BGL Eğitim Scripti")
    log.info("=" * 55)

    df           = prepare_data()
    X, tfidf, le = extract_features(df)
    iso, rf      = train(df, X)
    save_extractor(tfidf, le)
    quick_test(iso, rf, tfidf, le)

    log.info("\n✅ Eğitim tamamlandı!")
    log.info("   Kaydedilen modeller: %s", MODEL_DIR)
    log.info("   Sıradaki adım      : python api/app.py")