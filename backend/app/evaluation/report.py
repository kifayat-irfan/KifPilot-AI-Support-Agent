"""Report generation for benchmark results."""

import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.evaluation.schemas import (
    BenchmarkResult,
    EvaluationResult,
    RegressionComparison,
    LeaderboardEntry,
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates reports from benchmark results in multiple formats."""
    
    def __init__(self, output_dir: str = "./benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save_report(
        self,
        result: "BenchmarkResult",
        formats: List[str] = None,
        prefix: str = None,
    ) -> Dict[str, str]:
        """
        Save benchmark result in multiple formats.
        
        Args:
            result: Benchmark result to save
            formats: List of formats ["json", "csv", "markdown"]
            prefix: Optional prefix for output files
            
        Returns:
            Dictionary mapping format to output file path
        """
        formats = formats or ["json", "markdown"]
        prefix = prefix or f"benchmark_{result.dataset_name}_{result.dataset_version}"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        output_files = {}
        
        for fmt in formats:
            if fmt == "json":
                path = self.output_dir / f"{prefix}_{timestamp}.json"
                self._save_json(result, path)
                output_files["json"] = str(path)
            elif fmt == "csv":
                path = self.output_dir / f"{prefix}_{timestamp}.csv"
                self._save_csv(result, path)
                output_files["csv"] = str(path)
            elif fmt == "markdown":
                path = self.output_dir / f"{prefix}_{timestamp}.md"
                self._save_markdown(result, path)
                output_files["markdown"] = str(path)
            else:
                logger.warning(f"Unknown format: {fmt}")
        
        logger.info(f"Saved benchmark report to {self.output_dir}")
        return output_files
    
    def _save_json(self, result: "BenchmarkResult", path: Path) -> None:
        """Save results as JSON."""
        data = result.model_dump(mode="json")
        # Convert datetime objects to ISO format strings
        data = self._serialize_datetime(data)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved JSON report to {path}")
    
    def _save_csv(self, result: "BenchmarkResult", path: Path) -> None:
        """Save results as CSV (one row per question)."""
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "benchmark_id", "question", "predicted_answer", "expected_answer",
                "precision_at_5", "recall_at_10", "mrr", "ndcg", "hit_rate",
                "citation_precision", "citation_recall",
                "similarity_score", "confidence_score", "hallucination_rate",
                "response_time_ms", "retrieval_time_ms", "generation_time_ms",
                "token_usage", "model_name", "timestamp"
            ])
            
            for r in result.results:
                writer.writerow([
                    r.benchmark_id,
                    r.question,
                    r.predicted_answer,
                    r.expected_answer,
                    r.precision_at_5,
                    r.recall_at_10,
                    r.mrr,
                    r.ndcg,
                    r.hit_rate,
                    r.citation_precision,
                    r.citation_recall,
                    r.similarity_score,
                    r.confidence_score,
                    r.hallucination_rate,
                    r.response_time_ms,
                    r.retrieval_time_ms,
                    r.generation_time_ms,
                    r.token_usage,
                    r.model_name,
                    r.timestamp.isoformat() if r.timestamp else "",
                ])
        
        logger.info(f"Saved CSV report to {path}")
    
    def _save_markdown(self, result: "BenchmarkResult", path: Path) -> None:
        """Save results as Markdown report."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown(result))
        
        logger.info(f"Saved Markdown report to {path}")
    
    def _generate_markdown(self, result: "BenchmarkResult") -> str:
        """Generate Markdown report."""
        lines = []
        
        # Header
        lines.append(f"# Benchmark Report: {result.dataset_name} v{result.dataset_version}")
        lines.append(f"\n**Run Date:** {result.completed_at or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Total Time:** {result.total_time_ms:.0f} ms")
        lines.append(f"**Questions:** {result.evaluated_questions} / {result.total_questions}")
        
        # Configuration
        lines.append("\n## Configuration")
        lines.append(f"- **Model:** {result.model_name or 'N/A'}")
        lines.append(f"- **Embedding Model:** {result.embedding_model or 'N/A'}")
        lines.append(f"- **Hybrid Search:** {'Enabled' if result.hybrid_search_enabled else 'Disabled'}")
        lines.append(f"- **Reranker:** {'Enabled' if result.reranker_enabled else 'Disabled'}")
        lines.append(f"- **Query Expansion:** {'Enabled' if result.query_expansion_enabled else 'Disabled'}")
        lines.append(f"- **Context Compression:** {'Enabled' if result.context_compression_enabled else 'Disabled'}")
        
        # Summary Metrics
        lines.append("\n## Summary Metrics")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Precision@5 | {result.precision_at_5:.4f} |")
        lines.append(f"| Recall@10 | {result.recall_at_10:.4f} |")
        lines.append(f"| MRR | {result.mrr:.4f} |")
        lines.append(f"| NDCG | {result.ndcg:.4f} |")
        lines.append(f"| Hit Rate | {result.hit_rate:.4f} |")
        lines.append(f"| Citation Precision | {result.citation_precision:.4f} |")
        lines.append(f"| Citation Recall | {result.citation_recall:.4f} |")
        lines.append(f"| Avg Similarity | {result.avg_similarity:.4f} |")
        lines.append(f"| Avg Confidence | {result.avg_confidence:.4f} |")
        lines.append(f"| Hallucination Rate | {result.hallucination_rate:.4f} |")
        lines.append(f"| Avg Response Time | {result.avg_response_time_ms:.1f} ms |")
        lines.append(f"| Avg Retrieval Time | {result.avg_retrieval_time_ms:.1f} ms |")
        lines.append(f"| Avg Generation Time | {result.avg_generation_time_ms:.1f} ms |")
        lines.append(f"| Avg Token Usage | {result.avg_token_usage:.1f} |")
        
        # Per-question results
        lines.append("\n## Per-Question Results")
        lines.append("| # | ID | Question | Precision@5 | Recall@10 | MRR | Similarity | Hallucination | Time (ms) |")
        lines.append("|---|----|----------|-------------|-----------|-----|------------|---------------|-----------|")
        
        for i, r in enumerate(result.results, 1):
            question_short = r.question[:80] + "..." if len(r.question) > 80 else r.question
            lines.append(f"| {i} | {r.benchmark_id} | {question_short} | "
                        f"{r.precision_at_5:.3f} | {r.recall_at_10:.3f} | {r.mrr:.3f} | "
                        f"{r.similarity_score:.3f} | {r.hallucination_rate:.3f} | "
                        f"{r.response_time_ms:.0f} |")
        
        return "\n".join(lines)
    
    def _serialize_datetime(self, obj: Any) -> Any:
        """Convert datetime objects to ISO format strings."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(v) for v in obj]
        return obj
    
    def compare_runs(
        self,
        current: "BenchmarkResult",
        baseline: Optional["BenchmarkResult"],
    ) -> "RegressionComparison":
        """Compare current benchmark with baseline."""
        from app.evaluation.schemas import RegressionComparison
        
        if not baseline:
            return RegressionComparison(
                current_run_id="current",
                baseline_run_id="baseline",
                summary="No baseline provided for comparison",
            )
        
        # Metrics to compare
        metrics = [
            "precision_at_5", "recall_at_10", "mrr", "ndcg", "hit_rate",
            "citation_precision", "citation_recall",
            "avg_similarity", "avg_confidence", "hallucination_rate",
            "avg_response_time_ms", "avg_retrieval_time_ms",
            "avg_generation_time_ms", "avg_token_usage",
        ]
        
        metric_changes = {}
        improved = []
        regressed = []
        unchanged = []
        
        for metric in metrics:
            current_val = getattr(current, metric, 0.0)
            baseline_val = getattr(baseline, metric, 0.0)
            delta = current_val - baseline_val
            
            # Determine if improved (lower is better for some metrics)
            lower_is_better = metric in ["hallucination_rate", "avg_response_time_ms", 
                                          "avg_retrieval_time_ms", "avg_generation_time_ms", 
                                          "avg_token_usage"]
            
            if lower_is_better:
                improved_flag = delta < -0.01
                regressed_flag = delta > 0.01
            else:
                improved_flag = delta > 0.01
                regressed_flag = delta < -0.01
            
            metric_changes[metric] = {
                "current": current_val,
                "baseline": baseline_val,
                "delta": delta,
                "improved": improved_flag,
                "regressed": regressed_flag,
                "significant": abs(delta) > 0.01,
            }
            
            if improved_flag:
                improved.append(metric)
            elif regressed_flag:
                regressed.append(metric)
            else:
                unchanged.append(metric)
        
        overall_improved = len(improved) > len(regressed)
        
        if overall_improved:
            summary = f"Overall improvement: {len(improved)} metrics improved, {len(regressed)} regressed"
        elif regressed:
            summary = f"Regression detected: {len(regressed)} metrics regressed, {len(improved)} improved"
        else:
            summary = "No significant changes"
        
        return RegressionComparison(
            current_run_id="current",
            baseline_run_id="baseline",
            metric_changes=metric_changes,
            improved_metrics=improved,
            regressed_metrics=regressed,
            unchanged_metrics=unchanged,
            overall_improved=overall_improved,
            summary=summary,
        )
    
    def generate_leaderboard(self, results: List["BenchmarkResult"]) -> List["LeaderboardEntry"]:
        """Generate leaderboard from multiple benchmark results."""
        entries = []
        for r in results:
            if r.evaluated_questions == 0:
                continue
            
            entry = LeaderboardEntry(
                run_id=f"{r.dataset_name}_{r.dataset_version}_{r.completed_at or datetime.utcnow().strftime('%Y%m%d')}",
                name=f"{r.dataset_name} v{r.dataset_version}",
                dataset_name=r.dataset_name,
                dataset_version=r.dataset_version,
                precision_at_5=r.precision_at_5,
                recall_at_10=r.recall_at_10,
                mrr=r.mrr,
                ndcg=r.ndcg,
                citation_precision=r.citation_precision,
                citation_recall=r.citation_recall,
                hallucination_rate=r.hallucination_rate,
                avg_response_time_ms=r.avg_response_time_ms,
                model_name=r.model_name,
                embedding_model=r.embedding_model,
                hybrid_search_enabled=r.hybrid_search_enabled,
                reranker_enabled=r.reranker_enabled,
                query_expansion_enabled=r.query_expansion_enabled,
                context_compression_enabled=r.context_compression_enabled,
            )
            entries.append(entry)
        
        # Sort by primary metric (e.g., MRR)
        entries.sort(key=lambda x: x.mrr, reverse=True)
        return entries


# Global instance
report_generator = ReportGenerator()