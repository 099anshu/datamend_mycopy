#!/usr/bin/env python
"""CI/CD benchmark script for regression testing.

Runs standardized benchmarks and compares against versioned baselines.
Exits with non-zero code if any metric regresses beyond threshold.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evaluation.benchmarks.runner import (
    BenchmarkRunner,
    BenchmarkConfig,
    ThresholdStrategy,
)
from datasets.synthetic.semi_synthetic import InjectionConfig


def _get_timercd_detector():
    """Lazy import TimeRCDDetector to avoid requiring time_rcd for non-CI commands."""
    from detectors.timercd import TimeRCDDetector
    return TimeRCDDetector()


def create_standard_configs() -> list[BenchmarkConfig]:
    """Create standard benchmark configurations for CI."""
    configs = []

    # Synthetic univariate
    configs.append(BenchmarkConfig(
        dataset_type="synthetic",
        num_samples=50,
        seq_len=1000,
        anomaly_sample_ratio=1.0,
        is_multivariate=False,
        use_attribute_set=True,
        seed=42,
        detector_name="timercd",
        threshold_strategy=ThresholdStrategy.BEST_F1,
    ))

    # Synthetic multivariate (5 features)
    configs.append(BenchmarkConfig(
        dataset_type="synthetic",
        num_samples=30,
        seq_len=1000,
        anomaly_sample_ratio=1.0,
        is_multivariate=True,
        num_features=5,
        use_attribute_set=True,
        seed=42,
        detector_name="timercd",
        threshold_strategy=ThresholdStrategy.BEST_F1,
    ))

    # Semi-synthetic ETTh1
    configs.append(BenchmarkConfig(
        dataset_type="semi_synthetic",
        tsdb_dataset="ETTh1",
        injection_config=InjectionConfig(
            anomaly_types=["spike", "drift"],
            anomaly_intensity=3.0,
            num_anomalies_per_sensor=5,
            seed=42,
        ),
        detector_name="timercd",
        threshold_strategy=ThresholdStrategy.BEST_F1,
    ))

    return configs


def get_baseline_name(config: BenchmarkConfig, detector_name: str) -> str:
    """Generate baseline name from config."""
    parts = [detector_name, config.dataset_type]
    if config.is_multivariate:
        parts.append(f"multivariate_{config.num_features}")
    else:
        parts.append("univariate")
    if config.tsdb_dataset:
        parts.append(config.tsdb_dataset)
    return "_".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Run CI benchmarks")
    parser.add_argument(
        "--baseline-dir",
        default="evaluation/benchmarks/baselines",
        help="Directory containing baseline JSON files"
    )
    parser.add_argument(
        "--regression-threshold",
        type=float,
        default=0.05,
        help="Relative regression threshold (default: 0.05 = 5%)"
    )
    parser.add_argument(
        "--update-baselines",
        action="store_true",
        help="Update baselines with current results (use after verified improvements)"
    )
    parser.add_argument(
        "--output-report",
        help="Output markdown report path"
    )
    args = parser.parse_args()

    # Initialize detector and runner
    detector = _get_timercd_detector()
    runner = BenchmarkRunner(detector, "timercd", baseline_dir=args.baseline_dir)

    # Get standard configs
    configs = create_standard_configs()

    print(f"Running {len(configs)} benchmark configurations...")
    print(f"Regression threshold: {args.regression_threshold * 100:.1f}%")
    print(f"Baseline directory: {args.baseline_dir}")

    all_results = []
    all_regressions = []
    all_improvements = []
    overall_passed = True

    for i, config in enumerate(configs):
        print(f"\n[{i+1}/{len(configs)}] {config.dataset_type} "
              f"{'multivariate' if config.is_multivariate else 'univariate'} "
              f"{config.tsdb_dataset or ''}")

        try:
            result = runner.run(config)
            all_results.append(result)

            baseline_name = get_baseline_name(config, runner.detector_name)

            if args.update_baselines:
                baseline_path = runner.save_baseline(result, baseline_name)
                print(f"  Updated baseline: {baseline_path}")
                continue

            comparison = runner.compare_to_baseline(
                result, baseline_name, args.regression_threshold
            )

            if "error" in comparison:
                print(f"  No baseline found: {baseline_name}")
                if args.update_baselines:
                    runner.save_baseline(result, baseline_name)
                    print(f"  Created new baseline")
                continue

            if comparison["passed"]:
                print(f"  PASSED")
            else:
                print(f"  FAILED - Regressions detected:")
                for reg in comparison["regressions"]:
                    print(f"    {reg['metric']}: {reg['current']:.4f} vs "
                          f"{reg['baseline']:.4f} ({reg['relative_diff']*100:+.1f}%)")
                    all_regressions.append({
                        "config": config.dataset_type,
                        **reg
                    })
                overall_passed = False

            if comparison["improvements"]:
                for imp in comparison["improvements"]:
                    print(f"    IMPROVED {imp['metric']}: {imp['current']:.4f} vs "
                          f"{imp['baseline']:.4f} ({imp['relative_diff']*100:+.1f}%)")
                    all_improvements.append({
                        "config": config.dataset_type,
                        **imp
                    })

        except Exception as e:
            print(f"  ERROR: {e}")
            overall_passed = False

    # Summary
    print("\n" + "=" * 60)
    print("CI BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Total configurations: {len(configs)}")
    print(f"Regressions: {len(all_regressions)}")
    print(f"Improvements: {len(all_improvements)}")
    print(f"Overall: {'PASSED' if overall_passed else 'FAILED'}")

    # Generate markdown report if requested
    if args.output_report:
        generate_report(all_results, all_regressions, all_improvements,
                       overall_passed, args.output_report)
        print(f"\nReport saved to: {args.output_report}")

    # Exit code
    if not overall_passed:
        print("\n❌ CI FAILED: Regressions detected!")
        sys.exit(1)
    else:
        print("\n✅ CI PASSED: No regressions detected")
        sys.exit(0)


def generate_report(
    results: list,
    regressions: list,
    improvements: list,
    passed: bool,
    output_path: str,
):
    """Generate markdown report."""
    with open(output_path, "w") as f:
        f.write("# CI Benchmark Report\n\n")
        f.write(f"**Status**: {'✅ PASSED' if passed else '❌ FAILED'}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- Configurations run: {len(results)}\n")
        f.write(f"- Regressions: {len(regressions)}\n")
        f.write(f"- Improvements: {len(improvements)}\n\n")

        f.write("## Results\n\n")
        f.write("| Dataset | Type | F1 | Precision | Recall | PR-AUC | ROC-AUC | Threshold |\n")
        f.write("|---------|------|-----|-----------|--------|--------|---------|-----------|\n")

        for result in results:
            config = result.config
            eval_result = result.evaluation_result
            if eval_result:
                f.write(f"| {config.tsdb_dataset or 'synthetic'} | "
                        f"{'multivariate' if config.is_multivariate else 'univariate'} | "
                        f"{eval_result.f1:.4f} | {eval_result.precision:.4f} | "
                        f"{eval_result.recall:.4f} | {eval_result.pr_auc:.4f} | "
                        f"{eval_result.roc_auc:.4f} | {eval_result.best_threshold:.4f} |\n")

        if regressions:
            f.write("\n## Regressions ❌\n\n")
            f.write("| Metric | Current | Baseline | Diff | Rel Diff |\n")
            f.write("|--------|---------|----------|------|----------|\n")
            for reg in regressions:
                f.write(f"| {reg['metric']} | {reg['current']:.4f} | "
                        f"{reg['baseline']:.4f} | {reg['absolute_diff']:+.4f} | "
                        f"{reg['relative_diff']*100:+.1f}% |\n")

        if improvements:
            f.write("\n## Improvements ✅\n\n")
            f.write("| Metric | Current | Baseline | Diff | Rel Diff |\n")
            f.write("|--------|---------|----------|------|----------|\n")
            for imp in improvements:
                f.write(f"| {imp['metric']} | {imp['current']:.4f} | "
                        f"{imp['baseline']:.4f} | {imp['absolute_diff']:+.4f} | "
                        f"{imp['relative_diff']*100:+.1f}% |\n")


if __name__ == "__main__":
    main()