import pytest

from vpn_analytics.metrics import activation_experiment_statistics


@pytest.mark.parametrize("n, activated", [(1, 1), (20, 0), (20, 20), (20, 4)])
def test_small_or_degenerate_groups_do_not_report_a_zero_width_ci(n, activated):
    records = [
        {"onboarding_variant": variant, "activated_7d": index < activated}
        for variant in ("control", "treatment")
        for index in range(n)
    ]
    result = activation_experiment_statistics(records)
    assert result["ciLow"] is None
    assert result["ciHigh"] is None
    assert result["pValue"] is None
    assert not result["statisticallySignificant"]


def test_adequate_equal_groups_have_a_real_interval():
    records = [
        {"onboarding_variant": variant, "activated_7d": index < 15}
        for variant in ("control", "treatment") for index in range(30)
    ]
    result = activation_experiment_statistics(records)
    assert result["pValue"] == 1
    assert result["ciLow"] < 0 < result["ciHigh"]
