import pytest

from app import ratios
from app.ratios import FAIL, INFO, INSUFFICIENT, PASS, WARN


@pytest.mark.parametrize("assets, liabilities, expected", [
    (90, 100, FAIL),     # 0.90
    (120, 100, WARN),    # 1.20
    (200, 100, PASS),    # 2.00
])
def test_current_ratio_bands(assets, liabilities, expected):
    assert ratios.current_ratio(assets, liabilities)["status"] == expected


def test_current_ratio_handles_zero_liabilities():
    result = ratios.current_ratio(100, 0)
    assert result["status"] == INSUFFICIENT
    assert result["value"] is None


def test_working_capital_negative_fails():
    assert ratios.working_capital(80, 100)["status"] == FAIL
    assert ratios.working_capital(150, 100)["value"] == 50


def test_cash_ratio_is_informational():
    assert ratios.cash_ratio(50, 100)["status"] == INFO


@pytest.mark.parametrize("debt, equity, expected", [
    (100, 100, PASS),    # 1.0
    (250, 100, WARN),    # 2.5
    (400, 100, FAIL),    # 4.0
    (100, -50, FAIL),    # negative equity
])
def test_debt_to_equity_bands(debt, equity, expected):
    assert ratios.debt_to_equity(debt, equity)["status"] == expected


@pytest.mark.parametrize("debt, assets, expected", [
    (40, 100, PASS),
    (60, 100, WARN),
    (80, 100, FAIL),
])
def test_debt_to_assets_bands(debt, assets, expected):
    assert ratios.debt_to_assets(debt, assets)["status"] == expected


@pytest.mark.parametrize("income, interest, expected", [
    (50, 100, FAIL),
    (150, 100, WARN),
    (250, -100, PASS),   # interest expense reported as a negative number
    (500, 100, PASS),
])
def test_interest_coverage_bands(income, interest, expected):
    assert ratios.interest_coverage(income, interest)["status"] == expected


@pytest.mark.parametrize("noi, debt_service, expected", [
    (90, 100, FAIL),
    (120, 100, WARN),
    (160, 100, PASS),
    (250, 100, PASS),
])
def test_dscr_bands(noi, debt_service, expected):
    assert ratios.dscr(noi, debt_service)["status"] == expected


def test_analyze_sample_company():
    result = ratios.analyze(ratios.SAMPLE_COMPANY)
    assert len(result["checks"]) == 7
    assert result["summary"]["verdict"] in {"LOW_RISK", "REVIEW", "HIGH_RISK"}
    assert sum(result["summary"]["counts"].values()) == 7


def test_analyze_high_risk_verdict():
    result = ratios.analyze({"current_assets": 50, "current_liabilities": 100})
    assert result["summary"]["verdict"] == "HIGH_RISK"


def test_analyze_with_no_data():
    assert ratios.analyze({})["summary"]["verdict"] == INSUFFICIENT


@pytest.mark.parametrize("bad", ["100", True, [1, 2]])
def test_rejects_non_numeric_input(bad):
    with pytest.raises(ValueError):
        ratios.analyze({"current_assets": bad, "current_liabilities": 100})


def test_rejects_non_object_body():
    with pytest.raises(ValueError):
        ratios.analyze([1, 2, 3])
