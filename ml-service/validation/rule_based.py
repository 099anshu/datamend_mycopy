"""
Rule-based validation engine for DataMend.

Implements deterministic data-quality checks (Objective #2 in the project
proposal): range checks, not-null checks, data-type checks, uniqueness
checks, and cross-field checks. Columns are auto-detected from the dataset
profile so a user only needs to supply a threshold/range/type per column
(or accept the auto-suggested defaults).

This module is intentionally dependency-light (pandas + pydantic only) so
it can run standalone, be unit tested without the ML stack, and be wired
into main.py as a new endpoint.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class RuleType(str, Enum):
    RANGE = "range"
    NOT_NULL = "not_null"
    DATA_TYPE = "data_type"
    UNIQUENESS = "uniqueness"
    CROSS_FIELD = "cross_field"


class Rule(BaseModel):
    """A single validation rule the user (or an auto-suggestion) defines."""

    column: str
    ruleType: RuleType
    # RANGE
    minValue: Optional[float] = None
    maxValue: Optional[float] = None
    # DATA_TYPE
    expectedType: Optional[Literal["numeric", "datetime", "categorical"]] = None
    # CROSS_FIELD: e.g. "endCol must be after startCol"
    compareColumn: Optional[str] = None
    comparator: Optional[Literal["greater_than", "less_than", "not_equal"]] = None
    # Human-readable description shown in the UI
    description: Optional[str] = None


class RuleViolation(BaseModel):
    rowIndex: int
    timestamp: Optional[datetime] = None
    column: str
    ruleType: RuleType
    value: Optional[str] = None
    message: str
    severity: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class ValidationReport(BaseModel):
    rowCount: int
    columnCount: int
    totalViolations: int
    violationsByRule: Dict[str, int]
    violationsByColumn: Dict[str, int]
    qualityScore: float = Field(description="0-100, higher is better")
    violations: List[RuleViolation]


def suggest_rules(df: pd.DataFrame, timestamp_column: Optional[str] = None) -> List[Rule]:
    """
    Auto-detect columns and propose sensible default rules for each,
    the way the ML pipeline already auto-detects columns for anomaly
    detection. The user can accept these as-is or override
    minValue/maxValue/expectedType before calling validate_dataset().
    """
    rules: List[Rule] = []

    for col in df.columns:
        if col == timestamp_column:
            rules.append(Rule(column=col, ruleType=RuleType.NOT_NULL,
                               description="Timestamp cannot be empty"))
            rules.append(Rule(column=col, ruleType=RuleType.DATA_TYPE,
                               expectedType="datetime",
                               description="Timestamp must be parseable as a date/time"))
            continue

        series = df[col]
        rules.append(Rule(column=col, ruleType=RuleType.NOT_NULL,
                           description=f"{col} cannot be empty"))

        if pd.api.types.is_numeric_dtype(series):
            numeric = series.dropna()
            if len(numeric) > 0:
                q1, q3 = np.percentile(numeric, [25, 75])
                iqr = q3 - q1
                # 3*IQR fence is a conventional default "plausible range";
                # user can tighten/loosen this via minValue/maxValue.
                lo = float(q1 - 3 * iqr) if iqr > 0 else float(numeric.min())
                hi = float(q3 + 3 * iqr) if iqr > 0 else float(numeric.max())
                rules.append(Rule(column=col, ruleType=RuleType.RANGE,
                                   minValue=lo, maxValue=hi,
                                   description=f"{col} should stay within [{lo:.2f}, {hi:.2f}]"))
            rules.append(Rule(column=col, ruleType=RuleType.DATA_TYPE,
                               expectedType="numeric",
                               description=f"{col} must be numeric"))
        else:
            rules.append(Rule(column=col, ruleType=RuleType.DATA_TYPE,
                               expectedType="categorical",
                               description=f"{col} must be a valid category/string"))

    return rules


def _check_not_null(df: pd.DataFrame, rule: Rule) -> List[RuleViolation]:
    mask = df[rule.column].isna()
    return [
        RuleViolation(
            rowIndex=int(idx), column=rule.column, ruleType=rule.ruleType,
            value=None, message=f"{rule.column} is null/missing", severity="HIGH",
        )
        for idx in df.index[mask]
    ]


def _check_range(df: pd.DataFrame, rule: Rule) -> List[RuleViolation]:
    if rule.minValue is None and rule.maxValue is None:
        return []
    series = pd.to_numeric(df[rule.column], errors="coerce")
    mask = pd.Series(False, index=df.index)
    if rule.minValue is not None:
        mask |= series < rule.minValue
    if rule.maxValue is not None:
        mask |= series > rule.maxValue
    mask &= series.notna()
    return [
        RuleViolation(
            rowIndex=int(idx), column=rule.column, ruleType=rule.ruleType,
            value=str(series.loc[idx]),
            message=f"{rule.column}={series.loc[idx]} is outside "
                    f"[{rule.minValue}, {rule.maxValue}]",
            severity="MEDIUM",
        )
        for idx in df.index[mask]
    ]


def _check_data_type(df: pd.DataFrame, rule: Rule) -> List[RuleViolation]:
    if rule.expectedType is None:
        return []
    series = df[rule.column]
    violations: List[RuleViolation] = []
    if rule.expectedType == "numeric":
        bad = pd.to_numeric(series, errors="coerce").isna() & series.notna()
    elif rule.expectedType == "datetime":
        bad = pd.to_datetime(series, errors="coerce").isna() & series.notna()
    else:  # categorical: anything non-null is acceptable, flag empty strings
        bad = series.astype(str).str.strip().eq("") & series.notna()
    for idx in df.index[bad]:
        violations.append(RuleViolation(
            rowIndex=int(idx), column=rule.column, ruleType=rule.ruleType,
            value=str(series.loc[idx]),
            message=f"{rule.column}={series.loc[idx]!r} does not match expected type "
                    f"'{rule.expectedType}'",
            severity="MEDIUM",
        ))
    return violations


def _check_uniqueness(df: pd.DataFrame, rule: Rule) -> List[RuleViolation]:
    series = df[rule.column]
    dup_mask = series.duplicated(keep="first") & series.notna()
    return [
        RuleViolation(
            rowIndex=int(idx), column=rule.column, ruleType=rule.ruleType,
            value=str(series.loc[idx]),
            message=f"{rule.column}={series.loc[idx]!r} duplicates an earlier row",
            severity="LOW",
        )
        for idx in df.index[dup_mask]
    ]


def _check_cross_field(df: pd.DataFrame, rule: Rule) -> List[RuleViolation]:
    if rule.compareColumn is None or rule.comparator is None:
        return []
    if rule.compareColumn not in df.columns:
        return []
    a = df[rule.column]
    b = df[rule.compareColumn]
    if rule.comparator == "greater_than":
        mask = a <= b
    elif rule.comparator == "less_than":
        mask = a >= b
    else:  # not_equal
        mask = a == b
    mask = mask & a.notna() & b.notna()
    return [
        RuleViolation(
            rowIndex=int(idx), column=rule.column, ruleType=rule.ruleType,
            value=str(a.loc[idx]),
            message=f"{rule.column}={a.loc[idx]} fails '{rule.comparator}' against "
                    f"{rule.compareColumn}={b.loc[idx]}",
            severity="MEDIUM",
        )
        for idx in df.index[mask]
    ]


_CHECKS = {
    RuleType.NOT_NULL: _check_not_null,
    RuleType.RANGE: _check_range,
    RuleType.DATA_TYPE: _check_data_type,
    RuleType.UNIQUENESS: _check_uniqueness,
    RuleType.CROSS_FIELD: _check_cross_field,
}


def validate_dataset(
    df: pd.DataFrame,
    rules: List[Rule],
    timestamp_column: Optional[str] = None,
) -> ValidationReport:
    """Run every rule against the dataframe and produce a ValidationReport."""
    all_violations: List[RuleViolation] = []

    for rule in rules:
        if rule.column not in df.columns:
            continue
        check_fn = _CHECKS[rule.ruleType]
        all_violations.extend(check_fn(df, rule))

    if timestamp_column and timestamp_column in df.columns:
        ts = pd.to_datetime(df[timestamp_column], errors="coerce")
        for v in all_violations:
            if 0 <= v.rowIndex < len(ts):
                candidate = ts.iloc[v.rowIndex]
                if pd.notna(candidate):
                    v.timestamp = candidate.to_pydatetime()

    violations_by_rule: Dict[str, int] = {}
    violations_by_column: Dict[str, int] = {}
    for v in all_violations:
        violations_by_rule[v.ruleType.value] = violations_by_rule.get(v.ruleType.value, 0) + 1
        violations_by_column[v.column] = violations_by_column.get(v.column, 0) + 1

    total_cells = max(len(df) * max(len(df.columns), 1), 1)
    quality_score = round(max(0.0, 100.0 * (1 - len(all_violations) / total_cells)), 2)

    return ValidationReport(
        rowCount=len(df),
        columnCount=len(df.columns),
        totalViolations=len(all_violations),
        violationsByRule=violations_by_rule,
        violationsByColumn=violations_by_column,
        qualityScore=quality_score,
        violations=all_violations,
    )
