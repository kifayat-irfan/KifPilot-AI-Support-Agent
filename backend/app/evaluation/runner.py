"""CLI runner for benchmark suite."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

from app.evaluation.schemas import BenchmarkConfig
from app.evaluation.benchmark import BenchmarkSuite, run_benchmark_cli
from app.evaluation.report import ReportGenerator
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for benchmark CLI."""
    parser = argparse.ArgumentParser(
        description="KifPilot Evaluation & Benchmark Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.evaluation.runner --dataset benchmarks/sample.json
  python -m app.evaluation.runner --dataset benchmarks/test.csv --output ./results --format json markdown
  python -m app.evaluation.runner --dataset benchmarks/test.json --model gpt-4 --max-questions 50 --parallel
        """
    )
    
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Path to benchmark dataset (JSON or CSV)",
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="./benchmark_results",
        help="Output directory for results",
    )
    
    parser.add_argument(
        "--format",
        nargs="+",
        choices=["json", "csv", "markdown"],
        default=["json", "markdown"],
        help="Output formats",
    )
    
    parser.add_argument(
        "--model",
        type=str,
        help="Model name for the benchmark run",
    )
    
    parser.add_argument(
        "--max-questions",
        type=int,
        help="Maximum number of questions to evaluate",
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run evaluations in parallel",
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers",
    )
    
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Timeout per question in seconds",
    )
    
    parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="Compare with baseline run",
    )
    
    parser.add_argument(
        "--baseline-id",
        type=str,
        help="Baseline run ID for comparison",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    return parser


async def run_benchmark(
    dataset_path: str,
    output_path: str = "./benchmark_results",
    output_formats: List[str] = None,
    model_name: Optional[str] = None,
    max_questions: Optional[int] = None,
    parallel: bool = False,
    max_workers: int = 4,
    timeout_seconds: float = 300.0,
    compare_baseline: bool = False,
    baseline_run_id: Optional[str] = None,
) -> int:
    """
    Run benchmark with given configuration.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    config = BenchmarkConfig(
        dataset_path=dataset_path,
        output_path=output_path,
        output_formats=output_formats or ["json", "markdown"],
        model_name=model_name,
        max_questions=max_questions,
        parallel=parallel,
        max_workers=max_workers,
        timeout_seconds=timeout_seconds,
    )
    
    try:
        # Run benchmark
        suite = BenchmarkSuite(config)
        result = await run_benchmark_cli(
            dataset_path=dataset_path,
            output_path=output_path,
            model_name=model_name,
            max_questions=max_questions,
            parallel=parallel,
            max_workers=max_workers,
        )
        
        # Save results
        report_gen = ReportGenerator(output_path)
        report_gen.save_results(result, formats=output_formats or ["json", "markdown"])
        
        # Print summary
        print("\n" + "="*60)
        print(f"BENCHMARK COMPLETED: {result.dataset_name} v{result.dataset_version}")
        print("="*60)
        print(f"Questions Evaluated: {result.evaluated_questions}/{result.total_questions}")
        print(f"Precision@5: {result.precision_at_5:.4f}")
        print(f"Recall@10: {result.recall_at_10:.4f}")
        print(f"MRR: {result.mrr:.4f}")
        print(f"NDCG: {result.ndcg:.4f}")
        print(f"Hit Rate: {result.hit_rate:.4f}")
        print(f"Citation Precision: {result.citation_precision:.4f}")
        print(f"Citation Recall: {result.citation_recall:.4f}")
        print(f"Hallucination Rate: {result.hallucination_rate:.4f}")
        print(f"Avg Response Time: {result.avg_response_time_ms:.1f} ms")
        print(f"Total Time: {result.total_time_ms:.0f} ms")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}", exc_info=True)
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level)
    
    # Run benchmark
    exit_code = asyncio.run(run_benchmark(
        dataset_path=args.dataset,
        output_path=args.output,
        output_formats=args.format,
        model_name=args.model,
        max_questions=args.max_questions,
        parallel=args.parallel,
        max_workers=args.workers,
        timeout_seconds=args.timeout,
        compare_baseline=args.compare_baseline,
        baseline_run_id=args.baseline_id,
    ))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()