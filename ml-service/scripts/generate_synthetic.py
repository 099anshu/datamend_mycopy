#!/usr/bin/env python
"""CLI for synthetic dataset generation and benchmarking."""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np

from datasets.synthetic.generator import (
    generate_dataset,
    save_dataset,
    load_dataset,
    get_supported_anomaly_types,
    get_supported_patterns,
)
from datasets.synthetic.semi_synthetic import (
    inject_anomalies_into_tsdb,
    inject_anomalies_into_array,
    InjectionConfig,
)
from evaluation.benchmarks.runner import (
    BenchmarkRunner,
    BenchmarkConfig,
    ThresholdStrategy,
)
from evaluation.benchmarks.ci_benchmark import main as ci_main


def _get_timercd_detector():
    """Lazy import TimeRCDDetector to avoid requiring time_rcd for generation-only commands."""
    from detectors.timercd import TimeRCDDetector
    return TimeRCDDetector()


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate synthetic dataset."""
    print(f"Generating {'multivariate' if args.multivariate else 'univariate'} dataset...")
    print(f"  Samples: {args.num_samples}")
    print(f"  Sequence length: {args.seq_len or 'random (100-10000)'}")
    print(f"  Anomaly ratio: {args.anomaly_ratio}")
    if args.multivariate:
        print(f"  Features: {args.num_features}")

    dataset = generate_dataset(
        num_samples=args.num_samples,
        seq_len=args.seq_len,
        anomaly_sample_ratio=args.anomaly_ratio,
        is_multivariate=args.multivariate,
        num_features=args.num_features,
        use_attribute_set=args.use_attribute_set,
        metrics=args.metrics.split(",") if args.metrics else None,
        seed=args.seed,
    )

    save_dataset(dataset, args.output)
    print(f"\nSaved {len(dataset)} samples to {args.output}")

    # Print summary
    total_anomalies = sum(s["labels"].sum() for s in dataset)
    total_points = sum(len(s["labels"]) for s in dataset)
    print(f"Total timesteps: {total_points}")
    print(f"Anomalous timesteps: {total_anomalies} ({total_anomalies/total_points*100:.2f}%)")

    return 0


def cmd_inject_tsdb(args: argparse.Namespace) -> int:
    """Inject anomalies into TSDB dataset."""
    print(f"Injecting anomalies into {args.dataset}...")

    config = InjectionConfig(
        target_sensors=args.sensors.split(",") if args.sensors else None,
        anomaly_types=args.metrics.split(",") if args.metrics else ["spike", "drift"],
        anomaly_intensity=args.intensity,
        anomaly_duration_range=(args.min_duration, args.max_duration),
        num_anomalies_per_sensor=args.count,
        placement=args.placement,
        periodic_interval=args.periodic_interval,
        avoid_high_score_regions=not args.no_avoid,
        high_score_threshold=args.threshold,
        seed=args.seed,
    )

    # Use TimeRCD for clean window detection if avoiding
    detector = None
    if config.avoid_high_score_regions:
        detector = _get_timercd_detector()

    result = inject_anomalies_into_tsdb(args.dataset, config, detector=detector)

    # Save as pickle
    save_dataset([result], args.output)
    print(f"Saved semi-synthetic dataset to {args.output}")

    # Print summary
    print(f"Sensors: {len(result['attribute']['sensor_names'])}")
    print(f"Target sensors: {result['attribute']['target_sensors']}")
    print(f"Anomalous timesteps: {result['labels'].sum()} / {len(result['labels'])} "
          f"({result['labels'].mean()*100:.2f}%)")

    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Run benchmark on dataset."""
    print("Running benchmark...")

    detector = _get_timercd_detector()
    runner = BenchmarkRunner(detector, "timercd")

    config = BenchmarkConfig(
        dataset_type=args.type,
        num_samples=args.num_samples,
        seq_len=args.seq_len,
        anomaly_sample_ratio=args.anomaly_ratio,
        is_multivariate=args.multivariate,
        num_features=args.num_features,
        use_attribute_set=args.use_attribute_set,
        metrics=args.metrics.split(",") if args.metrics else None,
        seed=args.seed,
        tsdb_dataset=args.tsdb_dataset,
        threshold_strategy=ThresholdStrategy(args.strategy),
        target_fpr=args.target_fpr,
        target_recall=args.target_recall,
        custom_threshold=args.threshold,
    )

    if args.type == "semi_synthetic" and args.tsdb_dataset is None:
        print("Error: --tsdb-dataset required for semi_synthetic type")
        return 1

    result = runner.run(config)

    # Print results
    print("\n" + "=" * 50)
    print("BENCHMARK RESULTS")
    print("=" * 50)
    eval_result = result.evaluation_result
    print(f"F1:          {eval_result.f1:.4f}")
    print(f"Precision:   {eval_result.precision:.4f}")
    print(f"Recall:      {eval_result.recall:.4f}")
    print(f"PR-AUC:      {eval_result.pr_auc:.4f}")
    print(f"ROC-AUC:     {eval_result.roc_auc:.4f}")
    print(f"Best Threshold: {eval_result.best_threshold:.4f}")

    if result.per_sensor_metrics:
        print("\nPer-Sensor Metrics:")
        for m in result.per_sensor_metrics:
            print(f"  {m.sensor_name}: F1={m.f1:.4f}, P={m.precision:.4f}, R={m.recall:.4f}")

    if result.aggregate_metrics:
        agg = result.aggregate_metrics
        print(f"\nAggregate (Macro): F1={agg.macro_f1:.4f}, P={agg.macro_precision:.4f}, R={agg.macro_recall:.4f}")

    if result.latency:
        lat = result.latency
        print(f"\nLatency: median={lat.median_latency:.1f}, p95={lat.p95_latency:.1f}, "
              f"mean={lat.mean_latency:.1f}, max={lat.max_latency:.1f}, "
              f"detection_rate={lat.detection_rate:.2%}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to {args.output}")

    if args.save_baseline:
        name = args.save_baseline
        path = runner.save_baseline(result, name)
        print(f"Baseline saved to {path}")

    return 0


def cmd_list_anomalies(args: argparse.Namespace) -> int:
    """List supported anomaly types."""
    print("Supported anomaly types:")
    for a in get_supported_anomaly_types():
        print(f"  {a}")
    return 0


def cmd_list_patterns(args: argparse.Namespace) -> int:
    """List supported pattern types."""
    print("Supported pattern types:")
    for p in get_supported_patterns():
        print(f"  {p}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Synthetic TSAD dataset generator and benchmarking CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic dataset")
    gen_parser.add_argument("-n", "--num-samples", type=int, default=100)
    gen_parser.add_argument("-l", "--seq-len", type=int, default=None,
                            help="Sequence length (default: random 100-10000)")
    gen_parser.add_argument("-r", "--anomaly-ratio", type=float, default=1.0,
                            help="Fraction of samples with anomalies (0-1)")
    gen_parser.add_argument("--multivariate", action="store_true",
                            help="Generate multivariate data")
    gen_parser.add_argument("-f", "--num-features", type=int, default=5,
                            help="Number of features for multivariate")
    gen_parser.add_argument("--use-attribute-set", action="store_true", default=True,
                            help="Use attribute-based generation (recommended)")
    gen_parser.add_argument("-m", "--metrics", type=str, default=None,
                            help="Comma-separated anomaly types (e.g., spike,drift)")
    gen_parser.add_argument("-s", "--seed", type=int, default=42)
    gen_parser.add_argument("-o", "--output", type=str, required=True,
                            help="Output pickle file path")
    gen_parser.set_defaults(func=cmd_generate)

    # inject-tsdb command
    inj_parser = subparsers.add_parser("inject-tsdb", help="Inject anomalies into TSDB dataset")
    inj_parser.add_argument("dataset", choices=["ETTh1", "ETTh2", "ETTm1", "ETTm2"])
    inj_parser.add_argument("-s", "--sensors", type=str, default=None,
                            help="Comma-separated target sensors (default: all)")
    inj_parser.add_argument("-m", "--metrics", type=str, default=None,
                            help="Comma-separated anomaly types")
    inj_parser.add_argument("-i", "--intensity", type=float, default=3.0,
                            help="Anomaly intensity in standard deviations")
    inj_parser.add_argument("--min-duration", type=int, default=10)
    inj_parser.add_argument("--max-duration", type=int, default=50)
    inj_parser.add_argument("-c", "--count", type=int, default=3,
                            help="Anomalies per sensor")
    inj_parser.add_argument("--placement", choices=["random", "periodic"], default="random")
    inj_parser.add_argument("--periodic-interval", type=int, default=None)
    inj_parser.add_argument("--no-avoid", action="store_true",
                            help="Don't avoid high-score regions")
    inj_parser.add_argument("--threshold", type=float, default=0.7,
                            help="TimeRCD score threshold for clean windows")
    inj_parser.add_argument("--seed", type=int, default=42)
    inj_parser.add_argument("-o", "--output", type=str, required=True)
    inj_parser.set_defaults(func=cmd_inject_tsdb)

    # benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run benchmark on dataset")
    bench_parser.add_argument("--type", choices=["synthetic", "semi_synthetic"],
                              default="synthetic")
    bench_parser.add_argument("-n", "--num-samples", type=int, default=50)
    bench_parser.add_argument("-l", "--seq-len", type=int, default=1000)
    bench_parser.add_argument("-r", "--anomaly-ratio", type=float, default=1.0)
    bench_parser.add_argument("--multivariate", action="store_true")
    bench_parser.add_argument("-f", "--num-features", type=int, default=5)
    bench_parser.add_argument("--use-attribute-set", action="store_true", default=True)
    bench_parser.add_argument("-m", "--metrics", type=str, default=None)
    bench_parser.add_argument("-s", "--seed", type=int, default=42)
    bench_parser.add_argument("--tsdb-dataset", choices=["ETTh1", "ETTh2", "ETTm1", "ETTm2"])
    bench_parser.add_argument("--strategy", choices=["best_f1", "fixed_fpr", "fixed_recall", "youdens_j"],
                              default="best_f1")
    bench_parser.add_argument("--target-fpr", type=float, default=0.05)
    bench_parser.add_argument("--target-recall", type=float, default=0.90)
    bench_parser.add_argument("--threshold", type=float, default=None,
                              help="Fixed threshold (overrides strategy)")
    bench_parser.add_argument("-o", "--output", type=str, default=None,
                              help="Output JSON file for results")
    bench_parser.add_argument("--save-baseline", type=str, default=None,
                              help="Save as baseline with given name")
    bench_parser.set_defaults(func=cmd_benchmark)

    # list-anomalies command
    list_anom_parser = subparsers.add_parser("list-anomalies", help="List supported anomaly types")
    list_anom_parser.set_defaults(func=cmd_list_anomalies)

    # list-patterns command
    list_pat_parser = subparsers.add_parser("list-patterns", help="List supported pattern types")
    list_pat_parser.set_defaults(func=cmd_list_patterns)

    # ci-benchmark command (delegates to ci_benchmark.py)
    ci_parser = subparsers.add_parser("ci-benchmark", help="Run CI regression benchmarks")
    ci_parser.add_argument("--baseline-dir", default="evaluation/benchmarks/baselines")
    ci_parser.add_argument("--regression-threshold", type=float, default=0.05)
    ci_parser.add_argument("--update-baselines", action="store_true")
    ci_parser.add_argument("--output-report", type=str, default=None)
    ci_parser.set_defaults(func=lambda args: ci_main())

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())