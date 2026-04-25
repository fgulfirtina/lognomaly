"""
LogNomaly - Flask REST API (Multi-Dataset & Smart Routing - In-Memory)
"""

import os, sys, re, uuid, logging, shutil
import numpy as np
import pandas as pd
import joblib
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from scipy.sparse import hstack, csr_matrix
from retrain_endpoint import register_retrain_endpoint

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

def clean_log(msg: str) -> str:
        """Mesajdaki gereksiz ID, IP ve sayıları maskeleyerek modelin asıl kelimelere odaklanmasını sağlar."""
        import re
        msg = re.sub(r'blk_-?\d+', '<BLK>', msg) # Blok ID'leri gizle
        msg = re.sub(r'/?\d+\.\d+\.\d+\.\d+:\d+', '<IP>', msg) # IP adreslerini gizle
        msg = re.sub(r'\b\d+\b', '<NUM>', msg) # Tekil sayıları gizle
        return msg

def extract_hour(log_line: str, dataset_type: str) -> int:
    """
    Extracts the hour of the day (0-23) from the log timestamp.
    Returns -1 if parsing fails.
    """
    import re
    try:
        if dataset_type == "HDFS":
            m = re.search(r'^\d{6}\s(\d{2})\d{4}', log_line)
            if m: return int(m.group(1))
        elif dataset_type == "BGL":
            m = re.search(r'\d{4}-\d{2}-\d{2}-(\d{2})\.\d{2}\.\d{2}', log_line)
            if m: return int(m.group(1))
    except Exception:
        pass
    return -1

# ======================================================================
#  Model Bundle (Multi-Dataset Uyumlu Sınıf)
# ======================================================================
class ModelBundle:
    def __init__(self, dataset_type="BGL"):
        self.dataset_type = dataset_type
        self.prefix = "hdfs_" if dataset_type == "HDFS" else ""
        self.iso = self.rf = self.tfidf = self.le = None
        self.feature_names = []
        self.loaded = False
        self.explainer = None

    def load(self):
        iso_name = f"{self.prefix}iso_forest.joblib"
        rf_name  = f"{self.prefix}rf_classifier.joblib"
        ext_name = f"{self.prefix}feature_extractor.joblib"

        for name in [iso_name, rf_name, ext_name]:
            p = os.path.join(MODEL_DIR, name)
            if not os.path.exists(p):
                raise FileNotFoundError(f"Bulunamadi: {p}")

        self.iso = joblib.load(os.path.join(MODEL_DIR, iso_name))
        self.rf  = joblib.load(os.path.join(MODEL_DIR, rf_name))
        ext      = joblib.load(os.path.join(MODEL_DIR, ext_name))

        if isinstance(ext, dict):
            self.tfidf = ext["tfidf"]
            self.le    = ext["level_encoder"]
            self.feature_names = ext.get("feature_names", [])
        else:
            self.tfidf = ext.tfidf
            self.le    = ext.level_encoder
            self.feature_names = getattr(ext, "feature_names", [])

        if XAIExplainer and self.rf is not None:
            try:
                self.explainer = XAIExplainer(self.rf, self.feature_names)
            except Exception as e:
                logger.error(f"[{self.dataset_type}] XAI Explainer hatası: {e}")

        self.loaded = True
        logger.info("✅ %s Modelleri Yüklendi. Feature: %d", self.dataset_type, self.iso.n_features_in_)

    def vectorize(self, level: str, message: str, hour: int) -> np.ndarray:
        safe = level if level in self.le.classes_ else "UNKNOWN"
        lenc = self.le.transform([safe]).reshape(1, 1)

        # +++ NEW UEBA TEMPORAL FEATURE +++
        hour_norm = (hour / 23.0) if hour != -1 else 0.5
        hour_arr = np.array([[hour_norm]])
        cleaned_msg = clean_log(message)
        tv   = self.tfidf.transform([cleaned_msg])
        
        return hstack([csr_matrix(np.hstack([lenc, hour_arr])), tv]).toarray()


# Global Model Sözlüğü
bundles = {
    "BGL": ModelBundle("BGL"),
    "HDFS": ModelBundle("HDFS")
}

# Modelleri Başlat
try:
    bundles["BGL"].load()
except Exception as e:
    logger.error(f"BGL Yükleme Hatası: {e}")

try:
    bundles["HDFS"].load()
except Exception as e:
    logger.warning(f"HDFS Modeli Henüz Yok: {e}")

rule_engine = RuleEngine()


register_retrain_endpoint(app, bundles, MODEL_DIR)

# ======================================================================
#  Yardımcı Fonksiyon (Akıllı Yönlendirme)
# ======================================================================
def detect_log_type(log_line: str) -> str:
    """Logun formatına veya kelimelerine bakarak HDFS mi BGL mi olduğunu anlar."""
    if re.match(r"^\d{6}\s+\d{6}\s+", log_line):
        return "HDFS"
    if "dfs.DataNode" in log_line or "Receiving block" in log_line or "blk_" in log_line:
        return "HDFS"
    return "BGL"

# ======================================================================
#  Pipeline
# ======================================================================
def run_pipeline(level: str, message: str, raw_log: str = None) -> dict:
    if raw_log is None:
        raw_log = message

    # 1. Akıllı Yönlendirme
    dataset_type = detect_log_type(raw_log)
    bundle = bundles[dataset_type]
    
    if not bundle.loaded:
        bundle = bundles["BGL"]
        dataset_type = "BGL (Fallback)"

    extracted_hour = extract_hour(raw_log, dataset_type)

    # 2. Kural Motoru
    rule_result = rule_engine.check(message)
    threat_type = rule_result["threat_type"]
    rule_score  = rule_result["score"]

    if rule_score and rule_score >= 0.8:
        return {
            "level": level, "message": message, "dataset_routed": dataset_type,
            "raw_log": raw_log, 
            "extracted_hour": extracted_hour, # Artık hata vermeyecek!
            "is_known_threat": True, "threat_type": threat_type,
            "matched_rule": threat_type, "if_prediction": -1,
            "if_anomaly_score": 1.0, "predicted_class": threat_type,
            "rf_confidence": 1.0, "final_risk_score": rule_score,
            "risk_level": _to_level(rule_score), "shap_explanation": {},
        }

    # 3. ML Analizi (Seçilen Uzman Model ile)
    extracted_hour = extract_hour(raw_log, dataset_type)
    x = bundle.vectorize(level, message, extracted_hour)
    iso_score    = float(bundle.iso.decision_function(x)[0])
    anomaly_prob = float(np.clip(1.0 - (np.clip(iso_score, -0.5, 0.5) + 0.5), 0, 1))
    iso_pred     = int(bundle.iso.predict(x)[0])

    probs           = bundle.rf.predict_proba(x)[0]
    predicted_class = bundle.rf.classes_[int(np.argmax(probs))]
    rf_conf         = float(np.max(probs))
    
    if predicted_class == "Normal":
        risk = anomaly_prob * 0.3 
    else:
        risk = 0.4 * anomaly_prob + 0.6 * rf_conf

    # SHAP verisi için boş başlangıç (Scope Hatasını Engeller)
    shap_data = {}

    # +++ YENİ: HYBRID SIEM OVERRIDE +++
    msg_lower = message.lower()
    if level in ["ERROR", "CRITICAL", "FATAL"] or "outofmemory" in msg_lower or "corrupted" in msg_lower:
        risk = max(risk, 0.85) 
        predicted_class = "SystemFailure"
    elif level in ["WARN", "WARNING"] or "missing" in msg_lower:
        risk = max(risk, 0.65) 
        if predicted_class == "Normal": 
            predicted_class = "SystemFailure"

    if threat_type and rule_score is None:
        risk = min(1.0, risk + 0.15)

    # SHAP Hesaplama
    if risk >= 0.50 and bundle.explainer:
        try:
            # SHAP kütüphanesi x[0]'ı alır, gerçek model özelliklerini kullanır
            shap_data = bundle.explainer.explain_prediction(x[0])
        except Exception as e:
            logger.warning(f"SHAP hatasi: {e}")

    return {
        "level": level, "message": message, "dataset_routed": dataset_type,
        "raw_log": raw_log, # +++ YENİ: Regex'in kesmediği orijinal, saatli log +++
        "extracted_hour": extracted_hour, # +++ YENİ: Sadece saat bilgisi +++
        "is_known_threat": False,
        "threat_type": predicted_class if predicted_class != "Normal" else None,
        "matched_rule": threat_type, "if_prediction": iso_pred,
        "if_anomaly_score": round(anomaly_prob, 4),
        "predicted_class": predicted_class,
        "rf_confidence": round(rf_conf, 4),
        "final_risk_score": round(float(risk), 4),
        "risk_level": _to_level(risk),
        "shap_explanation": shap_data,
        "dataset_routed": dataset_type,
    }

def _to_level(s):
    return "High" if s >= 0.80 else ("Medium" if s >= 0.50 else "Low")

def _stats(results):
    if not results: return {"total": 0}
    total = len(results)
    dist  = {"Low": 0, "Medium": 0, "High": 0}
    types = {}
    
    # +++ YENİ: İlk logun nereye yönlendirildiğine bakıp tüm setin adını koyuyoruz +++
    dataset_type = results[0].get("dataset_routed", "Unknown") if total > 0 else "Unknown"
    
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
        "dataset_routed": dataset_type # Dashboard'a gidecek olan sihirli veri!
    }

_sessions = {}

# ======================================================================
#  Endpoints
# ======================================================================
@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "bgl_loaded": bundles["BGL"].loaded,
        "hdfs_loaded": bundles["HDFS"].loaded,
    })

@app.post("/api/analyze/single")
def analyze_single():
    body     = request.get_json(silent=True) or {}
    log_line = body.get("log", "").strip()
    level    = body.get("level", "INFO").strip().upper()
    if not log_line:
        return jsonify({"error": "'log' alani bos olamaz."}), 400
    try:
        result = run_pipeline(level, log_line)
        return jsonify(result), 200
    except Exception as e:
        logger.exception("Hata")
        return jsonify({"error": str(e)}), 500

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
    body      = request.get_json(silent=True) or {}
    file_path = body.get("file_path", "")
    session_id = body.get("session_id", "")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Dosya bulunamadi."}), 400
    try:
        records = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.strip()
                if not line: continue
                
                # Regex ile uğraşmıyoruz, satırı olduğu gibi modele yolluyoruz!
                records.append({
                    "level": "INFO", # Varsayılan seviye
                    "message": line, 
                    "raw": line
                })
                
        # Pipeline'a yolla
        results = [run_pipeline(r["level"], r["message"], r["raw"]) for r in records]
        
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