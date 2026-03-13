"""
LogNomaly - XAI Explainer
FR-09: SHAP değerleriyle model kararını açıkla
"""

import logging
import numpy as np
import shap

logger = logging.getLogger(__name__)


class XAIExplainer:
    """
    FR-09: Random Forest modelinin kararını SHAP TreeExplainer ile açıklar.
    Yüksek riskli tahminler için hangi özelliğin ne kadar katkı yaptığını
    JSON formatında döndürür.
    """

    def __init__(self, rf_model, feature_names: list[str]):
        """
        Args:
            rf_model: Eğitilmiş RandomForestModel örneği
            feature_names: FeatureExtractor.feature_names listesi
        """
        self.feature_names = feature_names
        logger.info("SHAP TreeExplainer oluşturuluyor...")
        self.explainer = shap.TreeExplainer(rf_model.model)
        logger.info("SHAP Explainer hazır.")

    def explain_prediction(self, feature_vector: np.ndarray,
                           top_n: int = 5) -> dict:
        """
        Tek bir örnek için SHAP açıklaması üretir.

        Args:
            feature_vector: (1, n_features) veya (n_features,) numpy array
            top_n: Döndürülecek en etkili feature sayısı

        Returns:
            {
              "top_features": [{"feature": str, "shap_value": float, "direction": str}],
              "base_value": float,
              "explanation_text": str
            }
        """
        x = feature_vector.reshape(1, -1)
        shap_values = self.explainer.shap_values(x)

        # Multi-class: şüpheli sınıf (index 1+) için değerleri al
        # shap_values shape: (n_classes, 1, n_features) veya (1, n_features)
        if isinstance(shap_values, list):
            # En yüksek mutlak katkıyı olan sınıfı seç
            class_idx = int(np.argmax([np.abs(sv).sum() for sv in shap_values]))
            sv = shap_values[class_idx][0]
            base_val = float(self.explainer.expected_value[class_idx])
        else:
            sv = shap_values[0]
            base_val = float(self.explainer.expected_value)

        # Top-N özellik seç
        abs_sv = np.abs(sv)
        top_indices = np.argsort(abs_sv)[::-1][:top_n]

        top_features = []
        for i in top_indices:
            name = self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}"
            val = float(sv[i])
            top_features.append({
                "feature": name,
                "shap_value": round(val, 4),
                "direction": "risk_artırıyor" if val > 0 else "risk_azaltıyor",
            })

        explanation_text = self._build_text(top_features)

        return {
            "top_features": top_features,
            "base_value": round(base_val, 4),
            "explanation_text": explanation_text,
        }

    def _build_text(self, top_features: list) -> str:
        """İnsan okunabilir kısa açıklama üretir."""
        pos = [f["feature"] for f in top_features if f["shap_value"] > 0]
        neg = [f["feature"] for f in top_features if f["shap_value"] < 0]
        parts = []
        if pos:
            parts.append(f"Riski artıran özellikler: {', '.join(pos[:3])}")
        if neg:
            parts.append(f"Riski azaltan özellikler: {', '.join(neg[:2])}")
        return ". ".join(parts) + "." if parts else "Açıklama üretilemedi."
