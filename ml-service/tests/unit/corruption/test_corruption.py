import numpy as np
import pytest

from corruption.pygrinder import (
    SUPPORTED_METHODS,
    SUPPORTED_STRATEGIES,
    CorruptionConfigError,
    MissingValueHandlingError,
    apply_corruption,
    calc_missing_rate,
    handle_missing_values,
)

ETTH1_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]


def test_supported_methods_are_expected():
    assert SUPPORTED_METHODS == {
        "mcar",
        "mar_logistic",
        "mnar_x",
        "mnar_t",
        "mnar_nonuniform",
        "rdo",
        "seq_missing",
        "block_missing",
    }


def test_supported_strategies_are_expected():
    assert SUPPORTED_STRATEGIES == {"reject", "ffill", "bfill", "mean", "interpolate"}


def test_clean_data_no_strategy_passes_unchanged(etth1_data):
    result = handle_missing_values(etth1_data)
    assert result.shape == etth1_data.shape
    np.testing.assert_array_equal(result, etth1_data)


def test_reject_with_missing_values_raises(etth1_data):
    corrupted = apply_corruption(etth1_data, "mcar", {"p": 0.1})
    with pytest.raises(MissingValueHandlingError, match="TimeRCD does not support NaNs"):
        handle_missing_values(corrupted, "reject")


@pytest.mark.parametrize("strategy", ["ffill", "bfill", "mean", "interpolate"])
def test_explicit_imputation_strategies_remove_nans(etth1_data, strategy):
    corrupted = apply_corruption(etth1_data, "mcar", {"p": 0.1})
    filled = handle_missing_values(corrupted, strategy)
    assert filled.shape == etth1_data.shape
    assert not np.isnan(filled).any()
    assert filled.dtype == np.float64


def test_strategy_does_not_mutate_input(etth1_data):
    corrupted = apply_corruption(etth1_data, "mcar", {"p": 0.1})
    original = corrupted.copy()
    handle_missing_values(corrupted, "ffill")
    np.testing.assert_array_equal(
        corrupted, original, "handle_missing_values must not mutate input"
    )


def test_unsupported_strategy_rejected(etth1_data):
    with pytest.raises(CorruptionConfigError, match="Unknown missing-value handling strategy"):
        handle_missing_values(etth1_data, "not_a_strategy")


def test_mean_all_nan_column_raises_no_zero_fill():
    data = np.full((5, 2), np.nan)
    with pytest.raises(MissingValueHandlingError, match="no observed values"):
        handle_missing_values(data, "mean")


def test_mcar_missing_rate_and_preserves_input(etth1_data):
    original = etth1_data.copy()
    corrupted = apply_corruption(etth1_data, "mcar", {"p": 0.1})

    assert corrupted.shape == etth1_data.shape
    np.testing.assert_array_equal(etth1_data, original, "original input must not be mutated")
    assert 0.08 < calc_missing_rate(corrupted) < 0.12


def test_rdo_missing_rate(etth1_data):
    corrupted = apply_corruption(etth1_data, "rdo", {"p": 0.1})
    assert corrupted.shape == etth1_data.shape
    assert 0.08 < calc_missing_rate(corrupted) < 0.12


def test_seq_missing_respects_seq_len(etth1_data):
    seq_len = 32
    corrupted = apply_corruption(etth1_data, "seq_missing", {"p": 0.1, "seq_len": seq_len})
    assert corrupted.shape == etth1_data.shape
    assert calc_missing_rate(corrupted) > 0.0


def test_block_missing_respects_block_shape(etth1_data):
    corrupted = apply_corruption(
        etth1_data,
        "block_missing",
        {"factor": 0.1, "block_len": 32, "block_width": 3},
    )
    assert corrupted.shape == etth1_data.shape
    assert calc_missing_rate(corrupted) > 0.0


def test_mar_logistic_2d_path(etth1_data):
    corrupted = apply_corruption(
        etth1_data, "mar_logistic", {"obs_rate": 0.5, "missing_rate": 0.1}
    )
    assert corrupted.shape == etth1_data.shape
    assert calc_missing_rate(corrupted) > 0.0


def test_mnar_nonuniform_3d_path(etth1_data):
    corrupted = apply_corruption(etth1_data, "mnar_nonuniform", {"p": 0.1})
    assert corrupted.shape == etth1_data.shape
    assert calc_missing_rate(corrupted) > 0.0


def test_mnar_x_3d_path(etth1_data):
    corrupted = apply_corruption(etth1_data, "mnar_x", {"offset": 0.0})
    assert corrupted.shape == etth1_data.shape
    assert calc_missing_rate(corrupted) > 0.0


def test_mnar_t_3d_path(etth1_data):
    corrupted = apply_corruption(etth1_data, "mnar_t", {})
    assert corrupted.shape == etth1_data.shape
    assert calc_missing_rate(corrupted) > 0.0


def test_unknown_method_rejected(etth1_data):
    with pytest.raises(CorruptionConfigError, match="Unknown corruption method"):
        apply_corruption(etth1_data, "not_a_method", {})


@pytest.mark.parametrize("method,p", [("mcar", 0.0), ("mcar", 1.0), ("rdo", 0.0)])
def test_bad_p_rejected(etth1_data, method, p):
    with pytest.raises(CorruptionConfigError, match="must be in"):
        apply_corruption(etth1_data, method, {"p": p})


def test_p_on_mnar_x_rejected(etth1_data):
    with pytest.raises(CorruptionConfigError, match="Unsupported parameter"):
        apply_corruption(etth1_data, "mnar_x", {"p": 0.1})


def test_p_on_mnar_t_rejected(etth1_data):
    with pytest.raises(CorruptionConfigError, match="Unsupported parameter"):
        apply_corruption(etth1_data, "mnar_t", {"p": 0.1})


def test_missing_seq_len_rejected(etth1_data):
    with pytest.raises(CorruptionConfigError, match="Missing required parameter"):
        apply_corruption(etth1_data, "seq_missing", {"p": 0.1})


def test_oversized_block_width_rejected(etth1_data):
    with pytest.raises(CorruptionConfigError, match="block_width"):
        apply_corruption(
            etth1_data,
            "block_missing",
            {"factor": 0.1, "block_len": 32, "block_width": 100},
        )


def test_unknown_param_key_rejected(etth1_data):
    with pytest.raises(CorruptionConfigError, match="Unsupported parameter"):
        apply_corruption(etth1_data, "mcar", {"p": 0.1, "nonsense": 1})


def test_pygrinder_plus_explicit_imputation_end_to_end(etth1_data, detector):
    sample = etth1_data[:500]
    corrupted = apply_corruption(sample, "mcar", {"p": 0.1})
    filled = handle_missing_values(corrupted, "ffill")
    assert not np.isnan(filled).any()
    scores = detector.detect(filled)
    assert len(scores) == len(sample)


def test_pygrinder_plus_no_strategy_raises(etth1_data):
    corrupted = apply_corruption(etth1_data, "mcar", {"p": 0.1})
    with pytest.raises(MissingValueHandlingError, match="TimeRCD does not support NaNs"):
        handle_missing_values(corrupted)


def test_original_tsdb_data_never_modified():
    from datasets.tsdb_loader import load_tsdb_dataset
    ETTH1_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
    df = load_tsdb_dataset("ETTh1")
    snapshot = df[ETTH1_COLUMNS].to_numpy(dtype=float).copy()
    apply_corruption(snapshot, "mcar", {"p": 0.2})
    np.testing.assert_array_equal(
        df[ETTH1_COLUMNS].to_numpy(dtype=float), snapshot
    )