"""Benchmark dataset loading and management."""

import json
import csv
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
import logging

from app.evaluation.schemas import (
    BenchmarkItem,
    BenchmarkDataset,
    BenchmarkConfig,
)

logger = logging.getLogger(__name__)


class BenchmarkDatasetLoader:
    """Loads and manages benchmark datasets from JSON or CSV files."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./.benchmark_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_from_json(self, path: str) -> BenchmarkDataset:
        """
        Load benchmark dataset from JSON file.
        
        Expected format:
        {
            "name": "dataset_name",
            "version": "1.0",
            "description": "Optional description",
            "items": [
                {
                    "id": "item_1",
                    "question": "What is...",
                    "expected_answer": "The answer is...",
                    "expected_documents": ["doc_1", "doc_2"],
                    "expected_pages": [1, 2],
                    "expected_sections": ["Introduction"],
                    "category": "general",
                    "difficulty": "easy",
                    "tags": ["tag1", "tag2"]
                }
            ],
            "metadata": {}
        }
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._parse_dataset(data, path.stem)
    
    def load_from_csv(self, path: str) -> BenchmarkDataset:
        """
        Load benchmark dataset from CSV file.
        
        Expected columns:
        id, question, expected_answer, expected_documents, expected_pages, 
        expected_sections, category, difficulty, tags
        
        Lists should be JSON-encoded strings or semicolon-separated values.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")
        
        items = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = self._parse_csv_row(row)
                if item:
                    items.append(item)
        
        return BenchmarkDataset(
            name=path.stem,
            version="1.0",
            description=f"Loaded from CSV: {path.name}",
            items=items,
            created_at=datetime.utcnow(),
            metadata={"source_file": str(path), "item_count": len(items)}
        )
    
    def _parse_csv_row(self, row: Dict[str, str]) -> Optional[BenchmarkItem]:
        """Parse a CSV row into a BenchmarkItem."""
        try:
            def parse_list(value: str) -> List[str]:
                if not value:
                    return []
                # Try JSON first
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(v) for v in parsed]
                except json.JSONDecodeError:
                    pass
                # Fallback to semicolon-separated
                return [v.strip() for v in value.split(';') if v.strip()]
            
            def parse_int_list(value: str) -> List[int]:
                if not value:
                    return []
                try:
                    return [int(v.strip()) for v in value.split(';') if v.strip()]
                except ValueError:
                    return []
            
            return BenchmarkItem(
                id=row.get('id', '').strip(),
                question=row.get('question', '').strip(),
                expected_answer=row.get('expected_answer', '').strip(),
                expected_documents=parse_list(row.get('expected_documents', '')),
                expected_pages=parse_int_list(row.get('expected_pages', '')),
                expected_sections=parse_list(row.get('expected_sections', '')),
                category=row.get('category', '').strip() or None,
                difficulty=row.get('difficulty', '').strip() or None,
                tags=parse_list(row.get('tags', '')),
            )
        except Exception as e:
            logger.warning(f"Failed to parse CSV row: {e}")
            return None
    
    def _parse_dataset(self, data: Dict[str, Any], default_name: str) -> BenchmarkDataset:
        """Parse raw JSON data into BenchmarkDataset."""
        items = []
        for item_data in data.get('items', []):
            try:
                item = BenchmarkItem(**item_data)
                items.append(item)
            except Exception as e:
                logger.warning(f"Failed to parse benchmark item: {e}")
        
        return BenchmarkDataset(
            name=data.get('name', default_name),
            version=data.get('version', '1.0'),
            description=data.get('description'),
            items=items,
            created_at=datetime.utcnow(),
            metadata=data.get('metadata', {})
        )
    
    def save_dataset(self, dataset: BenchmarkDataset, path: str) -> None:
        """Save benchmark dataset to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "name": dataset.name,
            "version": dataset.version,
            "description": dataset.description,
            "items": [item.model_dump() for item in dataset.items],
            "metadata": dataset.metadata,
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved benchmark dataset to {path} ({len(dataset.items)} items)")
    
    def get_dataset_hash(self, dataset: BenchmarkDataset) -> str:
        """Generate a hash for dataset versioning."""
        content = f"{dataset.name}|{dataset.version}|{len(dataset.items)}"
        for item in dataset.items:
            content += f"|{item.id}|{item.question}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class BenchmarkDatasetRegistry:
    """Registry for managing multiple benchmark datasets."""
    
    def __init__(self, datasets_dir: str = "./benchmarks"):
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.loader = BenchmarkDatasetLoader()
        self._registry: Dict[str, BenchmarkDataset] = {}
    
    def register(self, dataset: BenchmarkDataset) -> None:
        """Register a dataset in the registry."""
        key = f"{dataset.name}:{dataset.version}"
        self._registry[key] = dataset
        # Also save to disk
        self.loader.save_dataset(dataset, self.datasets_dir / f"{dataset.name}_v{dataset.version}.json")
    
    def load(self, name: str, version: str = "1.0") -> Optional[BenchmarkDataset]:
        """Load a dataset from registry or disk."""
        key = f"{name}:{version}"
        if key in self._registry:
            return self._registry[key]
        
        # Try loading from disk
        for ext in ['.json', '.csv']:
            path = self.datasets_dir / f"{name}_v{version}{ext}"
            if path.exists():
                if ext == '.json':
                    dataset = self.loader.load_from_json(str(path))
                else:
                    dataset = self.loader.load_from_csv(str(path))
                self._registry[key] = dataset
                return dataset
        
        return None
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all available datasets."""
        result = []
        for path in self.datasets_dir.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                result.append({
                    "name": data.get("name"),
                    "version": data.get("version"),
                    "description": data.get("description"),
                    "item_count": len(data.get("items", [])),
                    "file": path.name,
                })
            except Exception:
                pass
        
        for path in self.datasets_dir.glob("*.csv"):
            result.append({
                "name": path.stem,
                "version": "1.0",
                "description": f"CSV dataset: {path.name}",
                "item_count": "unknown",
                "file": path.name,
            })
        
        return result
    
    def get_default_dataset(self) -> Optional[BenchmarkDataset]:
        """Get a default sample dataset for testing."""
        # Create a minimal default dataset
        items = [
            BenchmarkItem(
                id="sample_1",
                question="What is the capital of France?",
                expected_answer="Paris is the capital of France.",
                expected_documents=["doc_france"],
                expected_pages=[1],
                expected_sections=["Geography"],
                category="geography",
                difficulty="easy",
                tags=["capital", "france"]
            ),
            BenchmarkItem(
                id="sample_2",
                question="How does photosynthesis work?",
                expected_answer="Photosynthesis converts light energy into chemical energy.",
                expected_documents=["doc_biology"],
                expected_pages=[5, 6],
                expected_sections=["Biology", "Science"],
                category="science",
                difficulty="medium",
                tags=["biology", "photosynthesis"]
            ),
        ]
        
        return BenchmarkDataset(
            name="default",
            version="1.0",
            description="Default sample benchmark dataset",
            items=items,
        )


def load_benchmark_dataset(config: "BenchmarkConfig") -> BenchmarkDataset:
    """Load benchmark dataset based on configuration."""
    loader = BenchmarkDatasetLoader()
    
    if config.dataset_path.endswith('.json'):
        return loader.load_from_json(config.dataset_path)
    elif config.dataset_path.endswith('.csv'):
        return loader.load_from_csv(config.dataset_path)
    else:
        raise ValueError(f"Unsupported dataset format: {config.dataset_path}")