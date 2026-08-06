"""Main benchmark orchestration."""

import time
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime

from app.evaluation.schemas import (
    BenchmarkItem,
    BenchmarkDataset,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkConfig,
    LeaderboardEntry,
    RegressionComparison,
)
from app.evaluation.datasets import load_benchmark_dataset, BenchmarkDatasetLoader
from app.evaluation.evaluator import Evaluator, BenchmarkRunner
from app.evaluation.report import ReportGenerator
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class BenchmarkSuite:
    """Main entry point for running benchmarks."""
    
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.evaluator = Evaluator()
        self.runner = BenchmarkRunner(self.config)
        self.report_generator = ReportGenerator()
        self.loader = BenchmarkDatasetLoader()
    
    async def run_benchmark(self, config: Optional[BenchmarkConfig] = None) -> "BenchmarkResult":
        """Run a complete benchmark suite."""
        config = config or self.config
        
        logger.info(f"Starting benchmark with dataset: {config.dataset_path}")
        
        # Load dataset
        dataset = load_benchmark_dataset(config)
        logger.info(f"Loaded dataset: {dataset.name} v{dataset.version} ({len(dataset.items)} items)")
        
        # Create evaluator and runner
        evaluator = Evaluator()
        runner = BenchmarkRunner(config)
        runner.evaluator = evaluator
        
        # Run benchmark
        result = await runner.run()
        
        return result
    
    def run_benchmark_sync(self, config: Optional[BenchmarkConfig] = None) -> "BenchmarkResult":
        """Synchronous wrapper for running benchmark."""
        return asyncio.run(self.run_benchmark(config))
    
    async def compare_with_baseline(
        self,
        current_result: "BenchmarkResult",
        baseline_run_id: str,
    ) -> "RegressionComparison":
        """Compare current results with a baseline run."""
        from app.evaluation.report import ReportGenerator
        
        # Load baseline (in production, load from database)
        # For now, return empty comparison
        report_gen = ReportGenerator()
        return report_gen.compare_runs(current_result, None)
    
    def save_results(self, result: "BenchmarkResult", output_path: str, formats: List[str] = None):
        """Save benchmark results in multiple formats."""
        from app.evaluation.report import ReportGenerator
        
        report_gen = ReportGenerator()
        formats = formats or ["json", "markdown"]
        report_gen.save_report(result, formats=formats)


async def run_benchmark_cli(
    dataset_path: str,
    output_path: str = "./benchmark_results",
    model_name: Optional[str] = None,
    max_questions: Optional[int] = None,
    output_formats: List[str] = None,
    parallel: bool = False,
    max_workers: int = 4,
) -> "BenchmarkResult":
    """CLI entry point for running benchmarks."""
    config = BenchmarkConfig(
        dataset_path=dataset_path,
        output_path=output_path,
        output_formats=output_formats or ["json", "markdown"],
        model_name=model_name,
        max_questions=max_questions,
        parallel=parallel,
        max_workers=max_workers,
    )
    
    suite = BenchmarkSuite(config)
    return await suite.run_benchmark(config)