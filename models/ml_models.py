"""
LogNomaly - ML Modelleri
FR-05: Layer 2 - Isolation Forest (unsupervised)
FR-06: Layer 3 - Random Forest (supervised)
Design Pattern: Strategy (BaseModel arayüzü)
"""

import logging
import numpy as np
import joblib
from abc import ABC, abstractmethod
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import cross_val_score

logger = logging.getLogger(__name__)


# ======================================================================
#  BaseModel — Strategy Pattern arayüzü
# ======================================================================
class BaseModel(ABC):
    """Tüm ML modellerinin uyması gereken sözleşme."""

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray | None = None):
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        ...

    @abstractmethod
    def save(self, path: str):
        ...

    @abstractmethod
    def load(self, path: str):
        ...


# ======================================================================
#  Layer 2: Isolation Forest
# ======================================================================
class IsolationForestModel(BaseModel):
    """
    FR-05: Bilinmeyen (zero-day) anomalileri tespit eder.
    predict() → -1 Anomali, +1 Normal
    decision_function() → ham anomali skoru (düşük = daha anomal)
    """

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100,
                 random_state: int = 42):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
        )
        self._is_fitted = False

    def train(self, X: np.ndarray, y=None):
        """Isolation Forest unsupervised — y parametresi yoksayılır."""
        logger.info("IsolationForest eğitimi başlıyor: X.shape=%s", X.shape)
        self.model.fit(X)
        self._is_fitted = True
        logger.info("IsolationForest eğitimi tamamlandı.")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """-1 = Anomali, +1 = Normal"""
        self._check_fitted()
        return self.model.predict(X)

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """
        Ham anomali skoru döndürür.
        Daha düşük skor → daha anomal.
        """
        self._check_fitted()
        return self.model.decision_function(X)

    def normalized_anomaly_score(self, X: np.ndarray) -> np.ndarray:
        """
        decision_function çıktısını [0, 1] aralığına normalize eder.
        0 = çok anomal, 1 = çok normal  →  biz 1-norm alarak
        "anomali olasılığı" olarak kullanacağız.
        """
        raw = self.decision_function(X)
        # Genellikle [-0.5, 0.5] civarında gelir; robust clip + normalize
        clipped = np.clip(raw, -0.5, 0.5)
        normalized = (clipped + 0.5)           # [0, 1]  (düşük = anomal)
        anomaly_prob = 1.0 - normalized         # anomali olasılığı
        return np.clip(anomaly_prob, 0.0, 1.0)

    def save(self, path: str):
        joblib.dump(self.model, path)
        logger.info("IsolationForest kaydedildi: %s", path)

    def load(self, path: str):
        self.model = joblib.load(path)
        self._is_fitted = True
        logger.info("IsolationForest yüklendi: %s", path)

    def _check_fitted(self):
        if not self._is_fitted:
            raise RuntimeError("Model henüz eğitilmedi. Önce train() çağır.")


# ======================================================================
#  Layer 3: Random Forest
# ======================================================================
class RandomForestModel(BaseModel):
    """
    FR-06: Anomali tipini sınıflandırır ve risk skoru (olasılık) üretir.
    predict_proba() → her sınıf için olasılık vektörü
    """

    # Varsayılan etiketler (HDFS/BGL datasetleri için tipik)
    DEFAULT_CLASSES = ['Normal', 'BruteForce', 'SQLi', 'SystemFailure', 'UnknownAnomaly']

    def __init__(self, n_estimators: int = 200, max_depth: int = 15,
                 random_state: int = 42):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            class_weight='balanced',
            n_jobs=-1,
        )
        self._is_fitted = False
        self.classes_: list[str] = []

    def train(self, X: np.ndarray, y: np.ndarray):
        """Etiketli veri ile eğitim."""
        logger.info("RandomForest eğitimi başlıyor: X.shape=%s, classes=%s",
                    X.shape, np.unique(y))
        self.model.fit(X, y)
        self.classes_ = list(self.model.classes_)
        self._is_fitted = True

        # Cross-validation skoru logla
        cv_scores = cross_val_score(self.model, X, y, cv=5, scoring='f1_weighted')
        logger.info("5-fold CV F1 skoru: %.3f ± %.3f", cv_scores.mean(), cv_scores.std())

    def predict(self, X: np.ndarray) -> np.ndarray:
        """En olası sınıf etiketini döndürür."""
        self._check_fitted()
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Her sınıf için olasılık matrisi (N, n_classes)."""
        self._check_fitted()
        return self.model.predict_proba(X)

    def predict_single(self, x: np.ndarray) -> dict:
        """
        Tek bir örnek için en olası sınıf + güven skoru döndürür.
        Returns: {"predicted_class": str, "confidence": float, "all_probs": dict}
        """
        self._check_fitted()
        probs = self.predict_proba(x.reshape(1, -1))[0]
        idx = int(np.argmax(probs))
        return {
            "predicted_class": self.classes_[idx],
            "confidence": float(probs[idx]),
            "all_probs": {cls: float(p) for cls, p in zip(self.classes_, probs)},
        }

    def save(self, path: str):
        joblib.dump(self.model, path)
        logger.info("RandomForest kaydedildi: %s", path)

    def load(self, path: str):
        self.model = joblib.load(path)
        self.classes_ = list(self.model.classes_)
        self._is_fitted = True
        logger.info("RandomForest yüklendi: %s", path)

    def _check_fitted(self):
        if not self._is_fitted:
            raise RuntimeError("Model henüz eğitilmedi. Önce train() çağır.")
