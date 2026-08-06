# Citation Pipeline

## Overview

Automatic citation generation, validation, and formatting for RAG responses with inline citation markers.

## Citation Flow

```
Retrieved Chunks → Context Builder → LLM Prompt → Answer → Citation Extractor → Validated Citations
                        │                    │            │
                        ▼                    ▼            ▼
              Adds [1], [2]          Generates      Matches [1],[2]
              markers                Answer         to source chunks
```

## Citation Models

```python
# services/rag/schemas.py
@dataclass
class Citation:
    id: str                      # "[1]", "[2]"
    document_id: str
    chunk_id: str
    text: str                    # Source text snippet (200 chars)
    score: float                 # Retrieval/rerank score
    page: int = None
    section: str = None
    heading: str = None
    metadata: dict = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "text": self.text,
            "score": self.score,
            "page": self.page,
            "section": self.section,
            "heading": self.heading
        }

@dataclass
class CitationMetrics:
    precision: float      # Of cited, how many are relevant
    recall: float         # Of relevant, how many cited
    f1: float
    avg_citations_per_answer: float
    citation_accuracy: float  # Citation text matches answer claim
```

## Context Builder with Citations

```python
# services/retrieval/context_builder.py
class ContextCompressionService:
    def build_context(
        self,
        query: str,
        results: List[RetrievalResult],
        reserved_tokens: int = 2000
    ) -> CompressedContext:
        available_tokens = self.max_tokens - reserved_tokens
        
        selected = self._select_chunks(results, available_tokens)
        
        context_parts = []
        citations = []
        total_tokens = 0
        
        for i, chunk in enumerate(selected):
            citation_id = f"[{i+1}]"
            chunk_tokens = self.tokenizer(chunk.text)
            
            if total_tokens + chunk_tokens > available_tokens:
                break
            
            # Add citation marker to context
            context_parts.append(f"{citation_id} {chunk.text}")
            
            # Build citation object
            citations.append(Citation(
                id=citation_id,
                document_id=chunk.metadata.get("document_id", ""),
                chunk_id=chunk.metadata.get("chunk_id", ""),
                text=chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                score=chunk.score,
                page=chunk.metadata.get("page"),
                section=chunk.metadata.get("section"),
                heading=chunk.metadata.get("heading"),
                metadata=chunk.metadata
            ))
            
            total_tokens += chunk_tokens
        
        return CompressedContext(
            context="\n\n".join(context_parts),
            citations=citations,
            total_tokens=total_tokens,
            chunks_used=len(citations),
            chunks_available=len(results)
        )
```

## Citation Extraction from Answer

```python
# services/rag/citations.py
class CitationExtractor:
    def __init__(
        self,
        max_citations: int = 10,
        fuzzy_threshold: float = 0.6
    ):
        self.max_citations = max_citations
        self.fuzzy_threshold = fuzzy_threshold
    
    def extract(
        self,
        answer: str,
        available_citations: List[Citation]
    ) -> List[Citation]:
        """Extract which citations are used in the answer"""
        used = []
        
        # 1. Explicit citation markers [1], [2], etc.
        explicit = self._extract_explicit(answer, available_citations)
        used.extend(explicit)
        
        # 2. If no explicit, try fuzzy matching
        if not used and available_citations:
            fuzzy = self._extract_fuzzy(answer, available_citations)
            used.extend(fuzzy)
        
        return used[:self.max_citations]
    
    def _extract_explicit(
        self,
        answer: str,
        available: List[Citation]
    ) -> List[Citation]:
        import re
        
        # Find [1], [2], [1, 2], [1-3] patterns
        cited_numbers = set()
        
        # Single citations [1]
        for match in re.finditer(r'\[(\d+)\]', answer):
            cited_numbers.add(int(match.group(1)))
        
        # Range citations [1-3]
        for match in re.finditer(r'\[(\d+)-(\d+)\]', answer):
            start, end = int(match.group(1)), int(match.group(2))
            cited_numbers.update(range(start, end + 1))
        
        # Comma-separated [1, 2, 3]
        for match in re.finditer(r'\[([\d,\s]+)\]', answer):
            for num_str in match.group(1).split(','):
                try:
                    cited_numbers.add(int(num_str.strip()))
                except ValueError:
                    pass
        
        # Map to citations
        used = []
        for num in sorted(cited_numbers):
            idx = num - 1
            if 0 <= idx < len(available):
                used.append(available[idx])
        
        return used
    
    def _extract_fuzzy(
        self,
        answer: str,
        available: List[Citation]
    ) -> List[Citation]:
        """Semantic matching when no explicit citations"""
        from difflib import SequenceMatcher
        
        answer_sentences = answer.split('.')
        used = []
        
        for citation in available:
            best_match = 0.0
            
            for sentence in answer_sentences:
                if len(sentence) < 20:
                    continue
                
                # Compare sentence with citation text
                ratio = SequenceMatcher(
                    None,
                    sentence.lower().strip(),
                    citation.text.lower().strip()
                ).ratio()
                
                best_match = max(best_match, ratio)
            
            if best_match >= self.fuzzy_threshold:
                used.append(citation)
        
        return used
```

## Citation Validation

```python
# services/rag/citations.py
class CitationValidator:
    def __init__(
        self,
        min_overlap: float = 0.1,
        max_citation_distance: int = 100  # chars from citation marker
    ):
        self.min_overlap = min_overlap
        self.max_distance = max_citation_distance
    
    def validate(
        self,
        answer: str,
        citations: List[Citation]
    ) -> CitationValidationResult:
        """Validate that citations actually support the answer"""
        issues = []
        validated = []
        
        for citation in citations:
            issue = self._check_citation(answer, citation)
            if issue:
                issues.append(issue)
            else:
                validated.append(citation)
        
        accuracy = len(validated) / max(len(citations), 1)
        
        return CitationValidationResult(
            citations=validated,
            issues=issues,
            accuracy=accuracy
        )
    
    def _check_citation(self, answer: str, citation: Citation) -> Optional[str]:
        # Find citation marker in answer
        marker = citation.id
        marker_pos = answer.find(marker)
        
        if marker_pos == -1:
            return f"Citation {marker} not found in answer"
        
        # Check proximity - citation should be near claim
        # Get text around marker
        start = max(0, marker_pos - self.max_distance)
        end = min(len(answer), marker_pos + self.max_distance)
        nearby_text = answer[start:end]
        
        # Check keyword overlap
        claim_words = set(nearby_text.lower().split())
        source_words = set(citation.text.lower().split())
        
        if not claim_words or not source_words:
            return f"Citation {marker}: empty text"
        
        overlap = len(claim_words & source_words) / max(len(claim_words), 1)
        
        if overlap < self.min_overlap:
            return f"Citation {marker}: low relevance ({overlap:.1%} overlap)"
        
        return None
```

## Citation Formatting

```python
# frontend/src/components/chat/CitationPanel.tsx
interface Citation {
  id: string;
  document_id: string;
  chunk_id: string;
  text: string;
  score: number;
  page?: number;
  section?: string;
  heading?: string;
}

const CitationPanel: React.FC<{ citations: Citation[] }> = ({ citations }) => {
  return (
    <div className="citation-panel">
      <h3>Sources ({citations.length})</h3>
      <div className="citations-list">
        {citations.map((citation, index) => (
          <CitationCard key={citation.id} citation={citation} index={index} />
        ))}
      </div>
    </div>
  );
};

const CitationCard: React.FC<{ citation: Citation; index: number }> = ({ 
  citation, index 
}) => {
  return (
    <div className="citation-card">
      <div className="citation-header">
        <span className="citation-id">{citation.id}</span>
        <span className="citation-score">Score: {(citation.score * 100).toFixed(0)}%</span>
      </div>
      <p className="citation-text">{citation.text}</p>
      <div className="citation-meta">
        {citation.page && <span>Page {citation.page}</span>}
        {citation.section && <span>Section: {citation.section}</span>}
        {citation.heading && <span>Heading: {citation.heading}</span>}
      </div>
      <button onClick={() => openDocument(citation.document_id)}>
        View Document
      </button>
    </div>
  );
};
```

## Citation Metrics

```python
# services/evaluation/metrics.py
class CitationMetrics:
    def __init__(self):
        pass
    
    def compute(
        self,
        answers: List[RAGResponse],
        ground_truth: List[GroundTruthCitation]
    ) -> CitationMetricsResult:
        """Compute citation quality metrics"""
        
        total_precision = 0
        total_recall = 0
        total_f1 = 0
        
        for answer, truth in zip(answers, ground_truth):
            pred_ids = set(c.id for c in answer.citations)
            true_ids = set(c.id for c in truth.citations)
            
            # Precision: of predicted, how many are correct
            tp = len(pred_ids & true_ids)
            fp = len(pred_ids - true_ids)
            fn = len(true_ids - pred_ids)
            
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * precision * recall / max(precision + recall, 1e-8)
            
            total_precision += precision
            total_recall += recall
            total_f1 += f1
        
        n = len(answers)
        return CitationMetricsResult(
            precision=total_precision / n,
            recall=total_recall / n,
            f1=total_f1 / n,
            avg_citations_per_answer=sum(len(a.citations) for a in answers) / n
        )
```

## Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # Citations
    RAG_MAX_CITATIONS: int = 5
    RAG_CITATION_FUZZY_THRESHOLD: float = 0.6
    RAG_CITATION_MIN_OVERLAP: float = 0.1
    RAG_CITATION_MAX_DISTANCE: int = 100
    
    # Citation validation
    RAG_VALIDATE_CITATIONS: bool = True
    RAG_CITATION_ACCURACY_THRESHOLD: float = 0.7
```

## Frontend Citation Display

```typescript
// src/types/citation.ts
export interface Citation {
  id: string;
  document_id: string;
  chunk_id: string;
  text: string;
  score: number;
  page?: number;
  section?: string;
  heading?: string;
  metadata?: Record<string, any>;
}

// src/hooks/useCitations.ts
export function useCitations(answer: string, citations: Citation[]) {
  const [expanded, setExpanded] = useState<string | null>(null);
  
  // Find citation markers in answer
  const citationRefs = answer.match(/\[\d+(?:[,-]\s*\d+)*\]/g) || [];
  
  return {
    citations,
    citationRefs,
    expanded,
    toggleExpand: (id: string) => setExpanded(expanded === id ? null : id)
  };
}
```