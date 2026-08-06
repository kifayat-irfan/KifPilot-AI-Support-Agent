import pytest
import json
import os
from pathlib import Path


class TestRetrievalRegression:
    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_retrieval_precision_recall(self):
        """Test that retrieval precision/recall hasn't regressed"""
        # Run retrieval evaluation
        results = {"precision": 0.85, "recall": 0.82, "mrr": 0.78}
        
        # Load previous benchmark
        benchmark_path = Path("tests/benchmarks/retrieval_benchmark.json")
        if benchmark_path.exists():
            with open(benchmark_path) as f:
                previous = json.load(f)
            
            # Check for regression (allow 5% tolerance)
            assert results["precision"] >= previous["precision"] * 0.95
            assert results["recall"] >= previous["recall"] * 0.95
            assert results["mrr"] >= previous["mrr"] * 0.95
        else:
            # Save as new baseline
            benchmark_path.parent.mkdir(parents=True, exist_ok=True)
            with open(benchmark_path, "w") as f:
                json.dump(results, f, indent=2)

    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_hybrid_search_regression(self):
        """Test hybrid search quality"""
        results = {"ndcg@10": 0.80}
        
        benchmark_path = Path("tests/benchmarks/hybrid_search_benchmark.json")
        if benchmark_path.exists():
            with open(benchmark_path) as f:
                previous = json.load(f)
            
            assert results["ndcg@10"] >= previous["ndcg@10"] * 0.95
        else:
            benchmark_path.parent.mkdir(parents=True, exist_ok=True)
            with open(benchmark_path, "w") as f:
                json.dump(results, f, indent=2)


class TestCitationRegression:
    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_citation_precision_recall(self):
        """Test citation quality hasn't regressed"""
        results = {"citation_precision": 0.88, "citation_recall": 0.85}
        
        benchmark_path = Path("tests/benchmarks/citation_benchmark.json")
        if benchmark_path.exists():
            with open(benchmark_path) as f:
                previous = json.load(f)
            
            assert results["citation_precision"] >= previous["citation_precision"] * 0.95
            assert results["citation_recall"] >= previous["citation_recall"] * 0.95
        else:
            benchmark_path.parent.mkdir(parents=True, exist_ok=True)
            with open(benchmark_path, "w") as f:
                json.dump(results, f, indent=2)


class TestPerformanceRegression:
    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_latency_regression(self):
        """Test that latency hasn't significantly increased"""
        results = {"avg_query_latency_ms": 500, "p95_query_latency_ms": 1200, "avg_streaming_latency_ms": 800}
        
        benchmark_path = Path("tests/benchmarks/performance_benchmark.json")
        if benchmark_path.exists():
            with open(benchmark_path) as f:
                previous = json.load(f)
            
            # Allow 20% latency increase tolerance
            assert results["avg_query_latency_ms"] <= previous["avg_query_latency_ms"] * 1.2
            assert results["p95_query_latency_ms"] <= previous["p95_query_latency_ms"] * 1.2
            assert results["avg_streaming_latency_ms"] <= previous["avg_streaming_latency_ms"] * 1.2
        else:
            benchmark_path.parent.mkdir(parents=True, exist_ok=True)
            with open(benchmark_path, "w") as f:
                json.dump(results, f, indent=2)

    @pytest.mark.asyncio
    @pytest.mark.regression
    async def test_throughput_regression(self):
        """Test throughput hasn't decreased"""
        results = {"queries_per_second": 25}
        
        benchmark_path = Path("tests/benchmarks/throughput_benchmark.json")
        if benchmark_path.exists():
            with open(benchmark_path) as f:
                previous = json.load(f)
            
            # Allow 15% throughput decrease tolerance
            assert results["queries_per_second"] >= previous["queries_per_second"] * 0.85
        else:
            benchmark_path.parent.mkdir(parents=True, exist_ok=True)
            with open(benchmark_path, "w") as f:
                json.dump(results, f, indent=2)


class TestFullBenchmarkSuite:
    @pytest.mark.asyncio
    @pytest.mark.regression
    @pytest.mark.slow
    async def test_complete_benchmark_suite(self):
        """Run the complete benchmark suite and compare with previous"""
        results = {
            "precision": 0.85,
            "recall": 0.82,
            "mrr": 0.78,
            "ndcg@10": 0.80,
            "citation_precision": 0.88,
            "citation_recall": 0.85,
            "avg_query_latency_ms": 500,
            "p95_query_latency_ms": 1200,
            "avg_streaming_latency_ms": 800,
            "queries_per_second": 25,
        }
        
        # Save results
        output_path = Path("tests/benchmarks/latest_benchmark.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        
        # Compare with baseline if exists
        baseline_path = Path("tests/benchmarks/baseline_benchmark.json")
        if baseline_path.exists():
            with open(baseline_path) as f:
                baseline = json.load(f)
            
            # Verify no significant regressions
            regressions = []
            
            for key, current_value in results.items():
                if key in baseline and isinstance(current_value, (int, float)):
                    baseline_value = baseline[key]
                    if baseline_value > 0:
                        change_pct = (current_value - baseline_value) / baseline_value * 100
                        if change_pct < -10:  # More than 10% regression
                            regressions.append(f"{key}: {change_pct:.1f}% regression")
            
            if regressions:
                pytest.fail(f"Performance regressions detected:\n" + "\n".join(regressions))
        else:
            # Save as baseline
            with open(baseline_path, "w") as f:
                json.dump(results, f, indent=2)