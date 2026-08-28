import pandas as pd
import pytest

from validation.rule_based import (
    Rule,
    RuleType,
    suggest_rules,
    validate_dataset,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
        ]),
        "age": [25, -5, 150, 40, None],
        "patient_id": ["p1", "p2", "p2", "p4", "p5"],
        "admission_date": pd.to_datetime([
            "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
        ]),
        "discharge_date": pd.to_datetime([
            "2024-01-02", "2024-01-01", "2024-01-05", "2024-01-04", "2024-01-06",
        ]),
    })


def test_not_null_flags_missing_value(sample_df):
    rule = Rule(column="age", ruleType=RuleType.NOT_NULL)
    report = validate_dataset(sample_df, [rule])
    assert report.totalViolations == 1
    assert report.violations[0].rowIndex == 4


def test_range_check_flags_out_of_bounds(sample_df):
    rule = Rule(column="age", ruleType=RuleType.RANGE, minValue=0, maxValue=120)
    report = validate_dataset(sample_df, [rule])
    flagged_rows = {v.rowIndex for v in report.violations}
    assert flagged_rows == {1, 2}  # -5 and 150


def test_uniqueness_flags_duplicate():
    df = pd.DataFrame({"email": ["a@x.com", "b@x.com", "a@x.com"]})
    rule = Rule(column="email", ruleType=RuleType.UNIQUENESS)
    report = validate_dataset(df, [rule])
    assert report.totalViolations == 1
    assert report.violations[0].rowIndex == 2


def test_cross_field_discharge_before_admission(sample_df):
    rule = Rule(
        column="discharge_date", ruleType=RuleType.CROSS_FIELD,
        compareColumn="admission_date", comparator="greater_than",
    )
    report = validate_dataset(sample_df, [rule])
    flagged_rows = {v.rowIndex for v in report.violations}
    # row 1: discharge (01-01) not > admission (01-02) -> violation
    assert 1 in flagged_rows


def test_data_type_check_flags_bad_numeric():
    df = pd.DataFrame({"value": ["10", "20", "abc", "30"]})
    rule = Rule(column="value", ruleType=RuleType.DATA_TYPE, expectedType="numeric")
    report = validate_dataset(df, [rule])
    assert report.totalViolations == 1
    assert report.violations[0].rowIndex == 2


def test_suggest_rules_covers_every_column(sample_df):
    rules = suggest_rules(sample_df, timestamp_column="timestamp")
    covered_columns = {r.column for r in rules}
    assert covered_columns == set(sample_df.columns)


def test_quality_score_is_100_when_clean():
    df = pd.DataFrame({"a": [1, 2, 3]})
    rule = Rule(column="a", ruleType=RuleType.NOT_NULL)
    report = validate_dataset(df, [rule])
    assert report.qualityScore == 100.0
