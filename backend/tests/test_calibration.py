import sys
import numpy as np
import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from prediction_engine import XGBoostPredictor


@pytest.fixture
def trained_predictor(tmp_path):
    """XGBoostPredictor entraîné sur données synthétiques."""
    pred = XGBoostPredictor()
    pred.model_file = str(tmp_path / "xgb_test.pkl")

    rng = np.random.default_rng(42)
    # 600 échantillons, 57 features (44 base + 3 fatigue + 10 stats)
    X = rng.standard_normal((600, 57))
    y = rng.integers(0, 3, size=600)

    pred.train(X[:400], y[:400])
    return pred, X, y


# ── Calibration ──────────────────────────────────────────────────────────────

def test_calibrate_sets_flag(trained_predictor):
    pred, X, y = trained_predictor
    assert not pred.is_calibrated
    pred.calibrate(X[400:500], y[400:500])
    assert pred.is_calibrated


def test_calibrate_requires_trained_model(tmp_path):
    pred = XGBoostPredictor()
    pred.model_file = str(tmp_path / "empty.pkl")
    # Simuler un prédicteur non entraîné (indépendamment de xgboost_model.pkl)
    pred.model = None
    pred.is_trained = False
    with pytest.raises(RuntimeError):
        pred.calibrate(np.zeros((10, 57)), np.zeros(10, dtype=int))


def test_calibrated_proba_sum_to_one(trained_predictor):
    pred, X, y = trained_predictor
    pred.calibrate(X[400:500], y[400:500])
    result = pred.predict(X[500:501])
    total = result['home'] + result['draw'] + result['away']
    assert abs(total - 1.0) < 1e-5


def test_save_load_preserves_calibration_flag(trained_predictor):
    pred, X, y = trained_predictor
    pred.calibrate(X[400:500], y[400:500])

    # Recharger depuis le fichier
    pred2 = XGBoostPredictor()
    pred2.model_file = pred.model_file
    pred2.load_model()

    assert pred2.is_calibrated
    assert pred2.is_trained


def test_save_load_old_format_still_works(trained_predictor, tmp_path):
    """Rétro-compatibilité : ancien format pickle (modèle brut sans dict)."""
    import pickle
    pred, X, y = trained_predictor

    # Simuler un fichier au format ancien (juste le modèle, pas de dict)
    old_file = str(tmp_path / "old_model.pkl")
    with open(old_file, 'wb') as f:
        pickle.dump(pred.model, f)

    pred2 = XGBoostPredictor()
    pred2.model_file = old_file
    pred2.load_model()

    assert pred2.is_trained
    assert not pred2.is_calibrated

# ── Taille du vecteur de features ────────────────────────────────────────────

def test_feature_vector_size():
    """Le vecteur de features doit faire 47 éléments (44 base + 3 fatigue)."""
    from prediction_engine import XGBoostPredictor
    xgb = XGBoostPredictor()
    feat = xgb.create_features(
        "Home", "Away",
        {"Home": 1500, "Away": 1500},
        {"Home": {"attack": 1.5, "defense": 1.2}, "Away": {"attack": 1.2, "defense": 1.3}},
    )
    assert feat.shape == (1, 57)
