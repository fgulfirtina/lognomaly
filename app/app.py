"""
LogNomaly - Flask REST API (Düzeltilmiş Versiyon)
"""

import os, sys, re, uuid, logging, shutil
import numpy as np
import pandas as pd
import joblib
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from scipy.sparse import hstack, csr_matrix

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

    
from models.rule_engine import RuleEngine

try:
    from models.xai_explainer import XAIExplainer
except ImportError:
    XAIExplainer = None
    print("UYARI: models.xai_explainer bulunamadı. XAI devre dışı kalacak.")

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger("api")

MODEL_DIR  = os.path.join(BASE_DIR, "saved_models")
UPLOAD_DIR = os.path.join(BASE_DIR, "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
CORS(app)

# ======================================================================
#  Model Bundle
# ======================================================================
class ModelBundle:
    def __init__(self):
        self.iso = self.rf = self.tfidf = self.le = None
        self.feature_names = []
        self.loaded = False
        self.explainer = None

    def load(self):
        for name in ["iso_forest.joblib", "rf_classifier.joblib", "feature_extractor.joblib"]:
            p = os.path.join(MODEL_DIR, name)
            if not os.path.exists(p):
                raise FileNotFoundError(f"Bulunamadi: {p}")

        self.iso = joblib.load(os.path.join(MODEL_DIR, "iso_forest.joblib"))
        self.rf  = joblib.load(os.path.join(MODEL_DIR, "rf_classifier.joblib"))
        ext      = joblib.load(os.path.join(MODEL_DIR, "feature_extractor.joblib"))

        if isinstance(ext, dict):
            self.tfidf = ext["tfidf"]
            self.le    = ext["level_encoder"]
            self.feature_names = ext.get("feature_names", [])
        else:
            self.tfidf = ext.tfidf
            self.le    = ext.level_encoder
            self.feature_names = getattr(ext, "feature_names", [])

        # XAI Explainer Başlatma
        if XAIExplainer and self.rf is not None:
            try:
                # RandomForestClassifier nesnesini doğrudan gönderiyoruz
                self.explainer = XAIExplainer(self.rf, self.feature_names)
                logger.info("XAI Explainer başarıyla başlatıldı.")
            except Exception as e:
                logger.error(f"XAI Explainer başlatma hatası: {e}")

        self.loaded = True
        logger.info("Modeller yuklendi. Feature: %d", self.iso.n_features_in_)

    def vectorize(self, level: str, message: str) -> np.ndarray:
    # Eski: safe = level if level in self.le.classes_ else "INFO"
        safe = level if level in self.le.classes_ else "UNKNOWN" # DÜZELTİLDİ
        lenc = self.le.transform([safe]).reshape(1, 1)
        td   = np.zeros((1, 1))
        tv   = self.tfidf.transform([message])
        return hstack([csr_matrix(np.hstack([lenc, td])), tv]).toarray()

bundle = ModelBundle()
try:
    bundle.load()
except Exception as e:
    logger.error(f"Model yükleme hatası: {e}")

# Kural motorunu başlat
rule_engine = RuleEngine()

# ======================================================================
#  Pipeline
# ======================================================================
def run_pipeline(level: str, message: str) -> dict:
    # Eski check_rules yerine yeni nesneyi kullanıyoruz
    rule_result = rule_engine.check(message)
    threat_type = rule_result["threat_type"]
    rule_score = rule_result["score"]

    # Katman 1: Kural Eşleşmesi (Kritik Skor)
    if rule_score and rule_score >= 0.8:
        return {
            "level": level, "message": message,
            "is_known_threat": True, "threat_type": threat_type,
            "matched_rule": threat_type, "if_prediction": -1,
            "if_anomaly_score": 1.0, "predicted_class": threat_type,
            "rf_confidence": 1.0, "final_risk_score": rule_score,
            "risk_level": _to_level(rule_score), "shap_explanation": {},
        }

    # Katman 2 & 3: ML Analizi
    x = bundle.vectorize(level, message)
    iso_score    = float(bundle.iso.decision_function(x)[0])
    anomaly_prob = float(np.clip(1.0 - (np.clip(iso_score, -0.5, 0.5) + 0.5), 0, 1))
    iso_pred     = int(bundle.iso.predict(x)[0])

    if iso_pred == 1:
        risk, predicted_class, rf_conf = anomaly_prob * 0.2, "Normal", 0.0
    else:
        probs           = bundle.rf.predict_proba(x)[0]
        predicted_class = bundle.rf.classes_[int(np.argmax(probs))]
        rf_conf         = float(np.max(probs))
        risk            = 0.4 * anomaly_prob + 0.6 * rf_conf

    if threat_type and rule_score is None:
        risk = min(1.0, risk + 0.15)

    # SHAP Analizi (Eğer risk yüksekse ve explainer hazırsa)
    shap_data = {}
    if risk >= 0.50 and bundle.explainer:
        try:
            # x[0] vektörünü explainer'a gönderiyoruz
            shap_data = bundle.explainer.explain_prediction(x[0])
        except Exception as e:
            logger.warning(f"SHAP hatasi: {e}")

    return {
        "level": level, "message": message,
        "is_known_threat": False,
        "threat_type": predicted_class if predicted_class != "Normal" else None,
        "matched_rule": threat_type, "if_prediction": iso_pred,
        "if_anomaly_score": round(anomaly_prob, 4),
        "predicted_class": predicted_class,
        "rf_confidence": round(rf_conf, 4),
        "final_risk_score": round(float(risk), 4),
        "risk_level": _to_level(risk),
        "shap_explanation": shap_data,
    }

def _to_level(s):
    return "High" if s >= 0.80 else ("Medium" if s >= 0.50 else "Low")

def _stats(results):
    if not results: return {"total": 0}
    total = len(results)
    dist  = {"Low": 0, "Medium": 0, "High": 0}
    types = {}
    for r in results:
        dist[r["risk_level"]] = dist.get(r["risk_level"], 0) + 1
        if r["threat_type"]:
            types[r["threat_type"]] = types.get(r["threat_type"], 0) + 1
    return {
        "total_logs": total,
        "total_anomalies": sum(1 for r in results if r["final_risk_score"] >= 0.5),
        "avg_risk_score": round(sum(r["final_risk_score"] for r in results) / total, 4),
        "risk_distribution": dist,
        "threat_types": types,
    }

_sessions = {}

# ======================================================================
#  Endpoints
# ======================================================================
@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "models_loaded": bundle.loaded,
        "xai_ready": bundle.explainer is not None,
        "n_features": bundle.iso.n_features_in_ if bundle.loaded else 0
    })

@app.post("/api/analyze/single")
def analyze_single():
    if not bundle.loaded:
        return jsonify({"error": "Modeller yuklenmedi."}), 503
    body     = request.get_json(silent=True) or {}
    log_line = body.get("log", "").strip()
    level    = body.get("level", "INFO").strip().upper()
    if not log_line:
        return jsonify({"error": "'log' alani bos olamaz."}), 400
    try:
        return jsonify(run_pipeline(level, log_line)), 200
    except Exception as e:
        logger.exception("Hata")
        return jsonify({"error": str(e)}), 500

# ... (Diğer upload ve analyze_file endpointleri aynı kalabilir) ...

@app.post("/api/upload")
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Dosya alani yok."}), 400
    file = request.files["file"]
    ext  = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in {".log", ".txt", ".csv"}:
        return jsonify({"error": f"Gecersiz uzanti: {ext}"}), 400
    session_id  = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    file_path = os.path.join(session_dir, secure_filename(file.filename))
    file.save(file_path)
    return jsonify({"session_id": session_id, "file_path": file_path}), 200

@app.post("/api/analyze")
def analyze_file_ep():
    if not bundle.loaded:
        return jsonify({"error": "Modeller yuklenmedi."}), 503
    body      = request.get_json(silent=True) or {}
    file_path = body.get("file_path", "")
    session_id = body.get("session_id", "")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Dosya bulunamadi."}), 400
    try:
        # BGL ve HDFS regex'leri
        bgl_re  = re.compile(r"^(?:-|[A-Z0-9_]+)\s+\d+\s+\d{4}\.\d{2}\.\d{2}\s+\S+\s+\S+\s+\S+\s+\S+\s+(\w+)\s+(.+)$")
        hdfs_re = re.compile(r"^\d{6}\s+\d{6}\s+\d+\s+(\w+)\s+[^\s:]+:\s+(.+)$")
        records = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.strip()
                if not line: continue
                m = bgl_re.match(line) or hdfs_re.match(line)
                records.append({
                    "level": m.group(1).upper() if m else "INFO",
                    "message": m.group(2) if m else line
                })
        results = [run_pipeline(r["level"], r["message"]) for r in records]
        if session_id:
            _sessions[session_id] = results
            shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)
        return jsonify({"stats": _stats(results), "results": results}), 200
    except Exception as e:
        logger.exception("Dosya analiz hatasi")
        return jsonify({"error": str(e)}), 500

@app.get("/api/stats/<session_id>")
def get_stats(session_id):
    if session_id not in _sessions:
        return jsonify({"error": "Session bulunamadi."}), 404
    return jsonify(_stats(_sessions[session_id])), 200

@app.get("/api/results/<session_id>")
def get_results(session_id):
    if session_id not in _sessions:
        return jsonify({"error": "Session bulunamadi."}), 404
    page, limit = int(request.args.get("page", 1)), int(request.args.get("limit", 100))
    data = _sessions[session_id]
    return jsonify({"page": page, "limit": limit, "total": len(data),
                    "results": data[(page-1)*limit:page*limit]}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)