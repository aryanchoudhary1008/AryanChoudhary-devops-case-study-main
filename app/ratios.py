"""Deterministic financial-ratio checks taken from the FinVeritas PBL project.

FinVeritas is an explainable financial background-check system. Its analysis layer
computes ratios from a company's financial statements and flags each one as
PASS / WARN / FAIL. This module extracts those checks into a small, dependency-free
library so they can be served as an independent microservice.

The thresholds mirror finveritas/analysis/metrics/{liquidity,solvency,dscr}.py.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
INFO = "INFO"
INSUFFICIENT = "INSUFFICIENT_DATA"

# A sample company used by the /api/v1/sample endpoint, smoke tests and load tests.
SAMPLE_COMPANY: Dict[str, float] = {
    "current_assets": 5_400_000,
    "current_liabilities": 3_100_000,
    "cash_and_equivalents": 1_250_000,
    "total_debt": 4_800_000,
    "total_equity": 2_900_000,
    "total_assets": 9_200_000,
    "operating_income": 1_150_000,
    "interest_expense": 420_000,
    "net_operating_income": 1_600_000,
    "annual_debt_service": 950_000,
}


def _number(data: Dict[str, Any], key: str) -> Optional[float]:
    """Read an optional numeric field, rejecting strings, booleans and other types."""
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{key}' must be a number")
    return float(value)


def _divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or abs(denominator) < 1e-9:
        return None
    return numerator / denominator


def _check(metric: str, value: Optional[float], unit: str, formula: str, status: str, detail: str) -> Dict[str, Any]:
    return {
        "metric": metric,
        "value": round(value, 2) if value is not None else None,
        "unit": unit,
        "formula": formula,
        "status": status,
        "detail": detail,
    }


# ── Liquidity ────────────────────────────────────────────────────────────────

def current_ratio(current_assets: Optional[float], current_liabilities: Optional[float]) -> Dict[str, Any]:
    formula = "Current Assets / Current Liabilities"
    ratio = _divide(current_assets, current_liabilities)
    if ratio is None:
        return _check("current_ratio", None, "x", formula, INSUFFICIENT,
                      "Current assets and non-zero current liabilities are required")
    if ratio < 1.0:
        status, detail = FAIL, f"Current ratio {ratio:.2f} below 1.0 - short-term assets don't cover short-term bills"
    elif ratio < 1.5:
        status, detail = WARN, f"Current ratio {ratio:.2f} is adequate but tight"
    else:
        status, detail = PASS, f"Current ratio {ratio:.2f} is healthy"
    return _check("current_ratio", ratio, "x", formula, status, detail)


def working_capital(current_assets: Optional[float], current_liabilities: Optional[float]) -> Dict[str, Any]:
    formula = "Current Assets - Current Liabilities"
    if current_assets is None or current_liabilities is None:
        return _check("working_capital", None, "currency", formula, INSUFFICIENT,
                      "Current assets and current liabilities are required")
    value = current_assets - current_liabilities
    if value < 0:
        return _check("working_capital", value, "currency", formula, FAIL,
                      "Negative working capital - current liabilities exceed current assets")
    return _check("working_capital", value, "currency", formula, PASS, "Positive working capital")


def cash_ratio(cash: Optional[float], current_liabilities: Optional[float]) -> Dict[str, Any]:
    formula = "Cash & Equivalents / Current Liabilities"
    ratio = _divide(cash, current_liabilities)
    if ratio is None:
        return _check("cash_ratio", None, "x", formula, INSUFFICIENT,
                      "Cash and non-zero current liabilities are required")
    return _check("cash_ratio", ratio, "x", formula, INFO,
                  f"Cash alone covers {ratio:.2f}x of current liabilities")


# ── Solvency ─────────────────────────────────────────────────────────────────

def debt_to_equity(total_debt: Optional[float], total_equity: Optional[float]) -> Dict[str, Any]:
    formula = "Total Debt / Total Equity"
    ratio = _divide(total_debt, total_equity)
    if ratio is None:
        return _check("debt_to_equity", None, "x", formula, INSUFFICIENT,
                      "Total debt and non-zero total equity are required")
    if ratio < 0:
        status, detail = FAIL, f"D/E {ratio:.2f} - negative equity (stockholders' deficit)"
    elif ratio > 3.0:
        status, detail = FAIL, f"D/E {ratio:.2f} - very high leverage"
    elif ratio > 2.0:
        status, detail = WARN, f"D/E {ratio:.2f} - elevated leverage"
    else:
        status, detail = PASS, f"D/E {ratio:.2f} - manageable leverage"
    return _check("debt_to_equity", ratio, "x", formula, status, detail)


def debt_to_assets(total_debt: Optional[float], total_assets: Optional[float]) -> Dict[str, Any]:
    formula = "Total Debt / Total Assets"
    ratio = _divide(total_debt, total_assets)
    if ratio is None:
        return _check("debt_to_assets", None, "x", formula, INSUFFICIENT,
                      "Total debt and non-zero total assets are required")
    if ratio > 0.7:
        status, detail = FAIL, f"D/A {ratio:.2f} - heavily leveraged"
    elif ratio > 0.5:
        status, detail = WARN, f"D/A {ratio:.2f} - moderate leverage"
    else:
        status, detail = PASS, f"D/A {ratio:.2f} - conservative balance sheet"
    return _check("debt_to_assets", ratio, "x", formula, status, detail)


def interest_coverage(operating_income: Optional[float], interest_expense: Optional[float]) -> Dict[str, Any]:
    formula = "Operating Income / |Interest Expense|"
    expense = abs(interest_expense) if interest_expense is not None else None
    ratio = _divide(operating_income, expense)
    if ratio is None:
        return _check("interest_coverage", None, "x", formula, INSUFFICIENT,
                      "Operating income and non-zero interest expense are required")
    if ratio < 1.0:
        status, detail = FAIL, f"ICR {ratio:.2f} - company cannot cover interest from operations"
    elif ratio < 2.0:
        status, detail = WARN, f"ICR {ratio:.2f} - tight interest coverage"
    elif ratio < 3.0:
        status, detail = PASS, f"ICR {ratio:.2f} - adequate"
    else:
        status, detail = PASS, f"ICR {ratio:.2f} - strong interest coverage"
    return _check("interest_coverage", ratio, "x", formula, status, detail)


# ── Debt service ─────────────────────────────────────────────────────────────

def dscr(net_operating_income: Optional[float], annual_debt_service: Optional[float]) -> Dict[str, Any]:
    formula = "Net Operating Income / Annual Debt Service"
    ratio = _divide(net_operating_income, annual_debt_service)
    if ratio is None:
        return _check("dscr", None, "x", formula, INSUFFICIENT,
                      "Net operating income and non-zero annual debt service are required")
    if ratio >= 2.0:
        status, detail = PASS, f"DSCR {ratio:.2f} - low risk, debt is comfortably serviced"
    elif ratio >= 1.5:
        status, detail = PASS, f"DSCR {ratio:.2f} - moderate risk, acceptable coverage"
    elif ratio >= 1.0:
        status, detail = WARN, f"DSCR {ratio:.2f} - high risk, little headroom"
    else:
        status, detail = FAIL, f"DSCR {ratio:.2f} - critical, income does not cover debt payments"
    return _check("dscr", ratio, "x", formula, status, detail)


# ── Grouped checks ───────────────────────────────────────────────────────────

def liquidity_checks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    ca = _number(data, "current_assets")
    cl = _number(data, "current_liabilities")
    cash = _number(data, "cash_and_equivalents")
    return [current_ratio(ca, cl), working_capital(ca, cl), cash_ratio(cash, cl)]


def solvency_checks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    debt = _number(data, "total_debt")
    return [
        debt_to_equity(debt, _number(data, "total_equity")),
        debt_to_assets(debt, _number(data, "total_assets")),
        interest_coverage(_number(data, "operating_income"), _number(data, "interest_expense")),
    ]


def debt_service_checks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [dscr(_number(data, "net_operating_income"), _number(data, "annual_debt_service"))]


def summarize(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Count statuses and derive an overall verdict for a list of checks."""
    counts = {PASS: 0, WARN: 0, FAIL: 0, INFO: 0, INSUFFICIENT: 0}
    for check in checks:
        counts[check["status"]] += 1
    if counts[FAIL]:
        verdict = "HIGH_RISK"
    elif counts[WARN]:
        verdict = "REVIEW"
    elif counts[PASS]:
        verdict = "LOW_RISK"
    else:
        verdict = INSUFFICIENT
    return {"verdict": verdict, "counts": counts}


def analyze(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run every check that the supplied figures allow."""
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")
    checks = liquidity_checks(data) + solvency_checks(data) + debt_service_checks(data)
    return {"checks": checks, "summary": summarize(checks)}
