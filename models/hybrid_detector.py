"""
LogNomaly - HybridDetector
Design Pattern: Facade — tüm pipeline'ı tek arayüzden yönetir.

FR-04: Layer 1 — Kural tabanlı filtreleme
FR-05: Layer 2 — Isolation Forest (unsupervised)
FR-06: Layer 3 — Random Forest (supervised)
FR-07: Probabilistic Risk Scoring
FR-08: Dynamic Thresholding & Alerting
FR-09: SHAP XAI
"""

import os
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum

from models.rule_engine import RuleEngine
from models.ml_models import IsolationForestModel, RandomForestModel
from models.xai_explainer import XAIExplainer
from utils.log_parser import LogParser
from utils.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'saved_models')


# ======================================================================
#  Risk Level enum (FR-08)
# ======================================================================
class RiskLevel(str, Enum):
    LOW      = "Low"       # 0.00 – 0.49  → Yeşil
    MEDIUM   = "Medium"    # 0.50 – 0.79  → Turuncu
    HIGH     = "High"      # 0.80 – 1.00  → Kırmızı
    CRITICAL = "Critical"  # Kural eşleşmesi → Kırmızı (anında)


def score_to_risk_level(score: float) -> RiskLevel:
    if score >= 0.80:
        return RiskLevel.HIGH
    if score >= 0.50:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


# ======================================================================
#  Sonuç veri yapısı
# ======================================================================
@dataclass
class AnalysisResult:
    raw_log: str
    level: str
    service: str
    message: str

    # Layer 1
    is_known_threat: bool = False
    matched_rule: str | None = None
    threat_type: str | None = None

    # Layer 2
    if_prediction: int = 1      # +1 Normal, -1 Anomali
    if_anomaly_score: float = 0.0

    # Layer 3
    predicted_class: str = "Normal"
    rf_confidence: float = 0.0

    # Final
    final_risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW

    # XAI
    shap_explanation: dict = field(default_factory=dict)


# ======================================================================
#  HybridDetector
# ======================================================================
class HybridDetector:
    """
    Facade: LogParser + FeatureExtractor + RuleEngine +
            IsolationForest + RandomForest + XAIExplainer'ı
            tek bir analyze() arayüzüyle sunar.
    """

    # Risk skoru ağırlıkları (FR-07)
    W_IF = 0.4
    W_RF = 0.6
    # SHAP açıklaması için minimum risk eşiği
    XAI_THRESHOLD = 0.50

    def __init__(self):
        self.parser     = LogParser()
        self.extractor  = FeatureExtractor()
        self.rule_engine = RuleEngine()
        self.if_model   = IsolationForestModel()
        self.rf_model   = RandomForestModel()
        self.explainer: XAIExplainer | None = None
        self._models_loaded = False

    # ------------------------------------------------------------------ #
    #  Model Yönetimi                                                     #
    # ------------------------------------------------------------------ #
    def load_models(self, model_dir: str = MODEL_DIR):
        """Kaydedilmiş modelleri diskten yükler."""
        os.makedirs(model_dir, exist_ok=True)
        if_path  = os.path.join(model_dir, 'iso_forest.joblib')
        rf_path  = os.path.join(model_dir, 'rf_classifier.joblib')
        ext_path = os.path.join(model_dir, 'feature_extractor.joblib')

        if not all(os.path.exists(p) for p in [if_path, rf_path, ext_path]):
            raise FileNotFoundError(
                f"Model dosyaları bulunamadı: {model_dir}\n"
                "Lütfen önce train.py ile modelleri eğitin."
            )

        self.if_model.load(if_path)
        self.rf_model.load(rf_path)
        self.extractor = FeatureExtractor.load(ext_path)
        self.explainer = XAIExplainer(self.rf_model, self.extractor.feature_names)
        self._models_loaded = True
        logger.info("Tüm modeller yüklendi.")

    def save_models(self, model_dir: str = MODEL_DIR):
        """Eğitilen modelleri diske kaydeder."""
        os.makedirs(model_dir, exist_ok=True)
        self.if_model.save(os.path.join(model_dir, 'iso_forest.joblib'))
        self.rf_model.save(os.path.join(model_dir, 'rf_classifier.joblib'))
        self.extractor.save(os.path.join(model_dir, 'feature_extractor.joblib'))

    # ------------------------------------------------------------------ #
    #  Ana Analiz: tek satır                                              #
    # ------------------------------------------------------------------ #
    def analyze_single_log(self, raw_log_string: str) -> AnalysisResult:
        """
        Tek bir ham log satırını tam pipeline'dan geçirir.
        """
        self._check_models()

        # Mini DataFrame oluştur
        df = self.parser.parse_file.__func__  # hint için
        single_df = pd.DataFrame([{
            'level': 'INFO', 'service': 'UNKNOWN',
            'message': raw_log_string, 'timestamp': pd.NaT,
            'raw': raw_log_string,
        }])
        # parse etmeden direkt extractor'a ver
        x = self.extractor.transform(single_df)
        return self._run_pipeline(x[0], raw_log_string, single_df.iloc[0])

    # ------------------------------------------------------------------ #
    #  Ana Analiz: dosya (batch)                                          #
    # ------------------------------------------------------------------ #
    def analyze_file(self, file_path: str) -> list[AnalysisResult]:
        """
        Tüm log dosyasını analiz eder. Liste olarak sonuç döndürür.
        """
        self._check_models()
        df = self.parser.parse_file(file_path)
        X = self.extractor.transform(df)

        results = []
        for i, (x, row) in enumerate(zip(X, df.itertuples(index=False))):
            result = self._run_pipeline(x, row.raw, row)
            results.append(result)

        logger.info("Dosya analizi tamamlandı: %d satır işlendi", len(results))
        return results

    # ------------------------------------------------------------------ #
    #  Pipeline Motoru                                                    #
    # ------------------------------------------------------------------ #
    def _run_pipeline(self, x: np.ndarray, raw: str, row) -> AnalysisResult:
        result = AnalysisResult(
            raw_log=raw,
            level=getattr(row, 'level', 'INFO'),
            service=getattr(row, 'service', 'UNKNOWN'),
            message=getattr(row, 'message', raw),
        )

        # ── Layer 1: Kural Tabanlı ─────────────────────────────────────
        rule_check = self.rule_engine.check(result.message)
        result.is_known_threat = rule_check["is_known_threat"]
        result.matched_rule    = rule_check["matched_rule"]
        result.threat_type     = rule_check["threat_type"]

        if result.is_known_threat:
            result.final_risk_score = 1.0
            result.risk_level       = RiskLevel.CRITICAL
            result.predicted_class  = rule_check["threat_type"]
            result.rf_confidence    = 1.0
            return result

        # ── Layer 2: Isolation Forest ──────────────────────────────────
        x2d = x.reshape(1, -1)
        result.if_prediction    = int(self.if_model.predict(x2d)[0])
        result.if_anomaly_score = float(self.if_model.normalized_anomaly_score(x2d)[0])

        if result.if_prediction == 1:  # Normal
            result.final_risk_score = result.if_anomaly_score * 0.2
            result.risk_level       = score_to_risk_level(result.final_risk_score)
            return result

        # ── Layer 3: Random Forest ─────────────────────────────────────
        rf_out = self.rf_model.predict_single(x)
        result.predicted_class = rf_out["predicted_class"]
        result.rf_confidence   = rf_out["confidence"]

        # FR-07: Ağırlıklı risk skoru
        result.final_risk_score = float(
            self.W_IF * result.if_anomaly_score +
            self.W_RF * result.rf_confidence
        )
        result.risk_level = score_to_risk_level(result.final_risk_score)

        # ── FR-09: XAI (yalnızca orta/yüksek risk için) ────────────────
        if result.final_risk_score >= self.XAI_THRESHOLD and self.explainer:
            try:
                result.shap_explanation = self.explainer.explain_prediction(x)
            except Exception as e:
                logger.warning("SHAP açıklaması üretilemedi: %s", e)

        return result

    def _check_models(self):
        if not self._models_loaded:
            raise RuntimeError(
                "Modeller yüklenmedi. Önce load_models() çağır "
                "veya train.py ile eğit."
            )
