"""
LogNomaly - Feature Extractor
FR-03: Sayısal özellik vektörlerine dönüşüm
"""

import logging
import numpy as np
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from scipy.sparse import hstack, issparse

logger = logging.getLogger(__name__)

LEVEL_ORDER = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'UNKNOWN']


class FeatureExtractor:
    """
    FR-03: Yapısal log DataFrame'ini ML modelleri için
    sayısal feature matrix'e dönüştürür.

    Features:
      - level_encoded  : log seviyesinin sayısal kodlaması
      - tfidf_*        : mesaj içeriğinin TF-IDF vektörü (100 feature)
      - time_delta     : ardışık loglar arası süre farkı (saniye)
      - hour           : log saati (0-23)
    """

    def __init__(self, max_tfidf_features: int = 100):
        self.max_tfidf_features = max_tfidf_features
        self.tfidf = TfidfVectorizer(
            max_features=max_tfidf_features,
            sublinear_tf=True,
            ngram_range=(1, 2),
        )
        self.level_encoder = LabelEncoder()
        self._is_fitted = False
        self.feature_names: list[str] = []

    # ------------------------------------------------------------------ #
    #  Fit + Transform (model eğitimi sırasında)                          #
    # ------------------------------------------------------------------ #
    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """Eğitim verisi üzerinde fit eder ve feature matrix döndürür."""
        level_enc = self._encode_levels(df['level'], fit=True)
        tfidf_mat = self.tfidf.fit_transform(df['message'].fillna(''))
        time_delta, hour = self._time_features(df)

        X = self._combine(level_enc, tfidf_mat, time_delta, hour)
        self._build_feature_names()
        self._is_fitted = True
        logger.info("fit_transform: %d satır → shape %s", len(df), X.shape)
        return X

    # ------------------------------------------------------------------ #
    #  Transform (inference sırasında)                                    #
    # ------------------------------------------------------------------ #
    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Eğitilmiş extractor ile yeni veriyi dönüştürür."""
        if not self._is_fitted:
            raise RuntimeError("FeatureExtractor henüz fit edilmedi. Önce fit_transform çağır.")

        level_enc = self._encode_levels(df['level'], fit=False)
        tfidf_mat = self.tfidf.transform(df['message'].fillna(''))
        time_delta, hour = self._time_features(df)

        X = self._combine(level_enc, tfidf_mat, time_delta, hour)
        return X

    # ------------------------------------------------------------------ #
    #  Kaydet / Yükle                                                     #
    # ------------------------------------------------------------------ #
    def save(self, path: str):
        joblib.dump(self, path)
        logger.info("FeatureExtractor kaydedildi: %s", path)

    @classmethod
    def load(cls, path: str) -> 'FeatureExtractor':
        obj = joblib.load(path)
        logger.info("FeatureExtractor yüklendi: %s", path)
        return obj

    # ------------------------------------------------------------------ #
    #  Yardımcı metodlar                                                  #
    # ------------------------------------------------------------------ #
    def _encode_levels(self, level_series: pd.Series, fit: bool) -> np.ndarray:
        # Bilinmeyen level'ları UNKNOWN olarak normalize et
        known = set(LEVEL_ORDER)
        normalized = level_series.apply(
            lambda x: x if x in known else 'UNKNOWN'
        )
        if fit:
            self.level_encoder.fit(LEVEL_ORDER)   # sabit sıra garantisi
        # transform sırasında görülmemiş label'ları UNKNOWN'a çevir
        safe = normalized.apply(
            lambda x: x if x in self.level_encoder.classes_ else 'UNKNOWN'
        )
        return self.level_encoder.transform(safe).reshape(-1, 1)

    def _time_features(self, df: pd.DataFrame):
        """Zaman farkı (saniye) ve saat bilgisi."""
        if 'timestamp' in df.columns and df['timestamp'].notna().any():
            ts = df['timestamp'].fillna(method='ffill').fillna(method='bfill')
            delta = ts.diff().dt.total_seconds().fillna(0).clip(0, 3600)
            hour = ts.dt.hour.fillna(0)
        else:
            delta = pd.Series(np.zeros(len(df)))
            hour  = pd.Series(np.zeros(len(df)))
        return delta.values.reshape(-1, 1), hour.values.reshape(-1, 1)

    def _combine(self, level_enc, tfidf_mat, time_delta, hour) -> np.ndarray:
        numeric = np.hstack([level_enc, time_delta, hour])   # (N, 3)
        if issparse(tfidf_mat):
            from scipy.sparse import csr_matrix
            combined = hstack([csr_matrix(numeric), tfidf_mat])
            return combined.toarray()
        return np.hstack([numeric, tfidf_mat])

    def _build_feature_names(self):
        tfidf_names = self.tfidf.get_feature_names_out().tolist()
        self.feature_names = ['level_encoded', 'time_delta_sec', 'hour'] + tfidf_names
