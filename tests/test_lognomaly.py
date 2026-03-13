"""
LogNomaly - Unit Testler
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import numpy as np
import pandas as pd
import tempfile

from utils.log_parser import LogParser, ValidationError
from utils.feature_extractor import FeatureExtractor
from models.rule_engine import RuleEngine
from models.ml_models import IsolationForestModel, RandomForestModel
from models.hybrid_detector import HybridDetector, RiskLevel, score_to_risk_level


# ======================================================================
#  LogParser Testleri
# ======================================================================
class TestLogParser:
    def setup_method(self):
        self.parser = LogParser(upload_dir=tempfile.mkdtemp())

    def _write_temp_log(self, lines: list[str]) -> str:
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.log',
                                        delete=False, dir=tempfile.mkdtemp())
        f.write('\n'.join(lines))
        f.close()
        return f.name

    def test_parse_standard_format(self):
        path = self._write_temp_log([
            "2025-01-20 14:30:15 ERROR [AuthService] Failed login attempt from IP 192.168.1.5",
            "2025-01-20 14:30:16 INFO [WebServer] Request processed in 45ms",
        ])
        df = self.parser.parse_file(path)
        assert len(df) == 2
        assert df.iloc[0]['level'] == 'ERROR'
        assert df.iloc[0]['service'] == 'AuthService'
        assert '192.168.1.5' in df.iloc[0]['message']

    def test_level_normalization(self):
        path = self._write_temp_log([
            "2025-01-20 10:00:00 WARN [App] disk space low",
            "2025-01-20 10:00:01 FATAL [App] system crash",
        ])
        df = self.parser.parse_file(path)
        assert 'WARNING' in df['level'].values
        assert 'CRITICAL' in df['level'].values

    def test_too_many_unparseable_raises(self):
        lines = ["!@#$%^" * 10] * 10   # tümü parse edilemez
        path = self._write_temp_log(lines)
        with pytest.raises(ValidationError, match="parse edilemedi"):
            self.parser.parse_file(path)

    def test_empty_file_raises(self):
        path = self._write_temp_log([])
        with pytest.raises(ValidationError, match="boş"):
            self.parser.parse_file(path)


# ======================================================================
#  FeatureExtractor Testleri
# ======================================================================
class TestFeatureExtractor:
    def _sample_df(self, n=50) -> pd.DataFrame:
        levels = ['INFO', 'ERROR', 'WARNING', 'DEBUG', 'CRITICAL']
        return pd.DataFrame({
            'level':     np.random.choice(levels, n),
            'service':   np.random.choice(['Auth', 'DB', 'Web'], n),
            'message':   [f"test message number {i}" for i in range(n)],
            'timestamp': pd.date_range("2025-01-01", periods=n, freq='1s'),
        })

    def test_fit_transform_shape(self):
        df  = self._sample_df(100)
        ext = FeatureExtractor(max_tfidf_features=50)
        X   = ext.fit_transform(df)
        # 3 sayısal + 50 tfidf = 53 feature
        assert X.shape == (100, 53)

    def test_transform_unseen_level(self):
        df_train = self._sample_df(50)
        df_test  = self._sample_df(10)
        df_test['level'] = 'TRACE'   # bilinmeyen level
        ext = FeatureExtractor()
        ext.fit_transform(df_train)
        X = ext.transform(df_test)   # hata vermemeli
        assert X.shape[0] == 10

    def test_feature_names_populated(self):
        ext = FeatureExtractor(max_tfidf_features=10)
        ext.fit_transform(self._sample_df())
        assert 'level_encoded' in ext.feature_names
        assert 'time_delta_sec' in ext.feature_names


# ======================================================================
#  RuleEngine Testleri
# ======================================================================
class TestRuleEngine:
    def setup_method(self):
        self.engine = RuleEngine()

    def test_brute_force_detected(self):
        r = self.engine.check("Failed login attempt from IP 192.168.1.1 (attempt 12)")
        assert r["is_known_threat"] is True
        assert r["threat_type"] == "BruteForce"

    def test_sqli_detected(self):
        r = self.engine.check("UNION SELECT username,password FROM users--")
        assert r["is_known_threat"] is True
        assert r["threat_type"] == "SQLi"

    def test_normal_log_not_flagged(self):
        r = self.engine.check("User admin logged in successfully from 10.0.0.5")
        assert r["is_known_threat"] is False

    def test_system_failure_detected(self):
        r = self.engine.check("kernel panic - not syncing: VFS unable to mount root fs")
        assert r["is_known_threat"] is True
        assert r["threat_type"] == "SystemFailure"


# ======================================================================
#  ML Model Testleri
# ======================================================================
class TestMLModels:
    def _make_X(self, n=200, n_feat=53):
        rng = np.random.default_rng(0)
        return rng.standard_normal((n, n_feat))

    def test_isolation_forest_train_predict(self):
        X = self._make_X()
        model = IsolationForestModel(contamination=0.05)
        model.train(X)
        preds = model.predict(X)
        assert set(preds).issubset({-1, 1})

    def test_isolation_forest_normalized_score_range(self):
        X = self._make_X()
        model = IsolationForestModel()
        model.train(X)
        scores = model.normalized_anomaly_score(X)
        assert scores.min() >= 0.0
        assert scores.max() <= 1.0

    def test_random_forest_train_predict(self):
        rng = np.random.default_rng(1)
        X = self._make_X()
        y = rng.choice(['Normal', 'BruteForce', 'SQLi'], len(X))
        model = RandomForestModel()
        model.train(X, y)
        preds = model.predict(X)
        assert len(preds) == len(X)

    def test_random_forest_predict_single(self):
        rng = np.random.default_rng(2)
        X = self._make_X()
        y = rng.choice(['Normal', 'BruteForce'], len(X))
        model = RandomForestModel()
        model.train(X, y)
        result = model.predict_single(X[0])
        assert "predicted_class" in result
        assert 0.0 <= result["confidence"] <= 1.0


# ======================================================================
#  Risk Level Testleri
# ======================================================================
class TestRiskLevel:
    def test_low(self):
        assert score_to_risk_level(0.0)  == RiskLevel.LOW
        assert score_to_risk_level(0.49) == RiskLevel.LOW

    def test_medium(self):
        assert score_to_risk_level(0.50) == RiskLevel.MEDIUM
        assert score_to_risk_level(0.79) == RiskLevel.MEDIUM

    def test_high(self):
        assert score_to_risk_level(0.80) == RiskLevel.HIGH
        assert score_to_risk_level(1.00) == RiskLevel.HIGH


# ======================================================================
#  Entegrasyon Testi (train + analyze)
# ======================================================================
class TestIntegration:
    def test_full_pipeline_with_demo_data(self, tmp_path):
        """Demo verisiyle eğit, sonra analiz yap — uçtan uca test."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from train import generate_demo_data, train

        model_dir = str(tmp_path / "models")
        df = generate_demo_data(n_normal=200, n_anomaly=50)
        train(df, model_dir=model_dir)

        det = HybridDetector()
        det.load_models(model_dir)

        result = det.analyze_single_log(
            "Failed login attempt from IP 10.0.0.1 (attempt 10)"
        )
        # Brute force kuralı tetiklenmeli
        assert result.is_known_threat is True
        assert result.final_risk_score == 1.0
        assert result.risk_level == RiskLevel.CRITICAL


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
