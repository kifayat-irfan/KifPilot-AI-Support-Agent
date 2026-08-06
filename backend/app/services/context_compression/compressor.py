"""Chunk compression logic for merging and low-value removal."""

import re
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CompressionResult:
    """Result of compression process."""
    chunks: List[Dict[str, Any]]
    merged_count: int
    low_value_removed_count: int
    removed_text_segments: List[str]


class ChunkCompressor:
    """Handles chunk merging and low-value text removal."""
    
    # Patterns for low-value content detection
    HEADER_FOOTER_PATTERNS = [
        r'(?i)^page \d+ of \d+$',
        r'(?i)^\d+$',  # standalone page numbers
        r'(?i)^copyright',
        r'(?i)^all rights reserved',
        r'(?i)^confidential',
        r'(?i)^internal use only',
        r'(?i)^draft',
        r'(?i)^version \d+',
        r'(?i)^table of contents',
        r'(?i)^index$',
        r'(?i)^appendix',
    ]
    
    BOILERPLATE_PATTERNS = [
        r'(?i)click here',
        r'(?i)read more',
        r'(?i)learn more',
        r'(?i)contact us',
        r'(?i)privacy policy',
        r'(?i)terms of service',
        r'(?i)cookie policy',
        r'(?i)subscribe',
        r'(?i)newsletter',
        r'(?i)follow us',
    ]
    
    NAVIGATION_PATTERNS = [
        r'(?i)^home\s*>\s*',
        r'(?i)^breadcrumb',
        r'(?i)^navigation',
        r'(?i)^menu\s*[:\-]',
        r'(?i)^skip to',
        r'(?i)^table of contents',
    ]

    def __init__(self, config: Dict[str, Any]):
        """Initialize the compressor with configuration."""
        self.remove_empty_lines = config.get("remove_empty_lines", True)
        self.remove_repeated_headers = config.get("remove_repeated_headers", True)
        self.remove_boilerplate = config.get("remove_boilerplate", True)
        self.remove_empty_lines_threshold = config.get("remove_empty_lines_threshold", 3)
        
        # Preservation flags
        self.preserve_tables = config.get("preserve_tables", True)
        self.preserve_lists = config.get("preserve_lists", True)
        self.preserve_code_blocks = config.get("preserve_code_blocks", True)
        self.preserve_warnings = config.get("preserve_warnings", True)
        self.preserve_notes = config.get("preserve_notes", True)
        self.preserve_headings = config.get("preserve_headings", True)
        self.preserve_page_numbers = config.get("preserve_page_numbers", True)
        
        # Compile patterns
        self._header_footer_regex = [re.compile(p) for p in self.HEADER_FOOTER_PATTERNS]
        self._boilerplate_regex = [re.compile(p) for p in self.BOILERPLATE_PATTERNS]
        self._navigation_regex = [re.compile(p) for p in self.NAVIGATION_PATTERNS]
    
    def compress(
        self,
        chunks: List[Dict[str, Any]],
        token_budget: Optional[int] = None,
    ) -> CompressionResult:
        """
        Compress chunks by merging adjacent and removing low-value content.
        
        Args:
            chunks: List of chunk dictionaries
            token_budget: Optional token budget to respect
            
        Returns:
            CompressionResult with compressed chunks and statistics
        """
        start_time = time.time()
        
        if not chunks:
            return CompressionResult(
                chunks=[],
                merged_count=0,
                low_value_removed_count=0,
                removed_text_segments=[]
            )
        
        # Step 1: Merge adjacent chunks from same document
        merged_chunks, merged_count = self._merge_adjacent_chunks(chunks)
        
        # Step 2: Remove low-value content
        filtered_chunks, low_value_count, removed_segments = self._remove_low_value(merged_chunks)
        
        # Step 3: Apply token budget if specified
        if token_budget:
            filtered_chunks = self._apply_token_budget(filtered_chunks, token_budget)
        
        total_time = (time.time() - start_time) * 1000
        
        logger.info(
            "Chunk compression completed",
            original_count=len(chunks),
            compressed_count=len(filtered_chunks),
            merged_count=merged_count,
            low_value_removed=low_value_count,
            time_ms=round(total_time, 2),
        )
        
        return CompressionResult(
            chunks=filtered_chunks,
            merged_count=merged_count,
            low_value_removed_count=low_value_count,
            removed_text_segments=removed_segments,
        )
    
    def _merge_adjacent_chunks(self, chunks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Merge adjacent chunks from the same document.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Tuple of (merged_chunks, merge_count)
        """
        if len(chunks) <= 1:
            return chunks, 0
        
        merged = []
        i = 0
        merge_count = 0
        
        while i < len(chunks):
            current = chunks[i]
            
            # Try to merge with next chunk
            if i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                
                if self._should_merge(current, next_chunk):
                    merged_chunk = self._merge_chunks(current, next_chunk)
                    merged.append(merged_chunk)
                    i += 2
                    merge_count += 1
                    continue
            
            merged.append(current)
            i += 1
        
        return merged, merge_count
    
    def _should_merge(self, chunk1: Dict[str, Any], chunk2: Dict[str, Any]) -> bool:
        """Determine if two chunks should be merged."""
        # Must be from same document
        doc1 = chunk1.get("document_id") or chunk1.get("metadata", {}).get("document_id")
        doc2 = chunk2.get("document_id") or chunk2.get("metadata", {}).get("document_id")
        
        if doc1 != doc2:
            return False
        
        # Check chunk indices are adjacent
        idx1 = chunk1.get("chunk_index") or chunk1.get("metadata", {}).get("chunk_index", 0)
        idx2 = chunk2.get("chunk_index") or chunk2.get("metadata", {}).get("chunk_index", 0)
        
        if abs(idx2 - idx1) != 1:
            return False
        
        # Check if combined text would be too large (heuristic)
        text1 = chunk1.get("text", "") or chunk1.get("content", "")
        text2 = chunk2.get("text", "") or chunk2.get("content", "")
        
        if len(text1) + len(text2) > 4000:  # ~1000 tokens max per chunk
            return False
        
        return True
    
    def _merge_chunks(self, chunk1: Dict[str, Any], chunk2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two adjacent chunks."""
        text1 = chunk1.get("text", "") or chunk1.get("content", "")
        text2 = chunk2.get("text", "") or chunk2.get("content", "")
        
        # Merge text with a separator
        merged_text = text1.rstrip() + "\n\n" + text2.lstrip()
        
        # Create merged chunk
        merged = chunk1.copy()
        merged["text"] = merged_text
        merged["content"] = merged_text
        merged["merged_from"] = [chunk1.get("chunk_id"), chunk2.get("chunk_id")]
        merged["merged_count"] = chunk1.get("merged_count", 1) + chunk2.get("merged_count", 1)
        
        # Update metadata
        meta1 = chunk1.get("metadata", {})
        meta2 = chunk2.get("metadata", {})
        merged_metadata = meta1.copy()
        merged_metadata["merged_from"] = merged_metadata.get("merged_from", []) + \
                                         meta2.get("merged_from", [chunk2.get("chunk_id")])
        
        merged["metadata"] = merged_metadata
        
        # Use higher score
        score1 = chunk1.get("score", 0) or chunk1.get("similarity_score", 0) or chunk1.get("final_score", 0) or chunk1.get("rrf_score", 0) or 0
        score2 = chunk2.get("score", 0) or chunk2.get("similarity_score", 0) or chunk2.get("final_score", 0) or chunk2.get("rrf_score", 0) or 0
        merged["score"] = max(score1, score2)
        merged["similarity_score"] = max(score1, score2)
        merged["final_score"] = max(score1, score2)
        merged["rrf_score"] = max(score1, score2)
        
        return merged
    
    def _remove_low_value(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int, List[str]]:
        """
        Remove low-value content from chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Tuple of (filtered_chunks, removed_count, removed_segments)
        """
        filtered = []
        removed_count = 0
        removed_segments = []
        
        for chunk in chunks:
            text = chunk.get("text", "") or chunk.get("content", "")
            
            if not text:
                continue
            
            # Check if chunk is entirely low-value
            if self._is_low_value_chunk(text):
                removed_count += 1
                removed_segments.append(text[:200])
                continue
            
            # Remove low-value segments from within the chunk
            cleaned_text, removed = self._clean_chunk_text(text)
            if removed:
                removed_segments.extend(removed)
            
            chunk_copy = chunk.copy()
            chunk_copy["text"] = cleaned_text
            chunk_copy["content"] = cleaned_text
            filtered.append(chunk_copy)
        
        return filtered, removed_count, removed_segments
    
    def _is_low_value_chunk(self, text: str) -> bool:
        """Check if entire chunk is low-value."""
        text_lower = text.lower().strip()
        
        # Very short chunks are suspicious
        if len(text_lower) < 20:
            # But preserve if it looks like a heading or code
            if self._looks_like_heading(text) or self._looks_like_code(text):
                return False
            return True
        
        # Check against boilerplate patterns
        for pattern in self._boilerplate_regex:
            if pattern.search(text_lower):
                return True
        
        # Check against navigation patterns
        for pattern in self._navigation_regex:
            if pattern.search(text_lower):
                return True
        
        return False
    
    def _looks_like_heading(self, text: str) -> bool:
        """Check if text looks like a heading."""
        stripped = text.strip()
        # Short, possibly ending with colon, or all caps
        if len(stripped) < 100:
            if stripped.endswith(':') or stripped.isupper():
                return True
            # Markdown headings
            if stripped.startswith('#'):
                return True
        return False
    
    def _looks_like_code(self, text: str) -> bool:
        """Check if text looks like code."""
        stripped = text.strip()
        if stripped.startswith('```') or stripped.startswith('    ') or stripped.startswith('\t'):
            return True
        # Common code patterns
        if re.search(r'(def|class|function|import|const|let|var)\s+\w+', stripped):
            return True
        return False
    
    def _clean_chunk_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Remove low-value segments from chunk text.
        
        Returns:
            Tuple of (cleaned_text, removed_segments)
        """
        removed_segments = []
        lines = text.split('\n')
        cleaned_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_stripped = line.strip()
            
            # Skip empty lines beyond threshold
            if not line_stripped:
                # Count consecutive empty lines
                empty_count = 1
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    empty_count += 1
                    j += 1
                
                if empty_count > self.remove_empty_lines_threshold:
                    # Remove excess empty lines, keep one
                    removed_segments.append(f"[{empty_count} empty lines removed]")
                    cleaned_lines.append("")  # Keep one empty line
                    i = j
                    continue
                else:
                    cleaned_lines.append(line)
                    i += 1
                    continue
            
            # Check for header/footer patterns
            is_header_footer = False
            for pattern in self._header_footer_regex:
                if pattern.search(line):
                    is_header_footer = True
                    removed_segments.append(f"Header/footer: {line_stripped[:100]}")
                    break
            
            if is_header_footer:
                i += 1
                continue
            
            # Check for boilerplate
            is_boilerplate = False
            for pattern in self._boilerplate_regex:
                if pattern.search(line):
                    is_boilerplate = True
                    removed_segments.append(f"Boilerplate: {line_stripped[:100]}")
                    break
            
            if is_boilerplate:
                i += 1
                continue
            
            # Check for navigation
            is_navigation = False
            for pattern in self._navigation_regex:
                if pattern.search(line):
                    is_navigation = True
                    removed_segments.append(f"Navigation: {line_stripped[:100]}")
                    break
            
            if is_navigation:
                i += 1
                continue
            
            # Check for repeated headers/footers (same line appearing multiple times)
            if self.remove_repeated_headers and self._is_repeated_line(line_stripped, lines):
                removed_segments.append(f"Repeated header/footer: {line_stripped[:100]}")
                i += 1
                continue
            
            # Preserve tables, lists, code blocks
            if self._is_preserved_content(line, lines, i):
                # Keep this line and related lines
                cleaned_lines.append(line)
                i += 1
                continue
            
            # Keep the line
            cleaned_lines.append(line)
            i += 1
        
        cleaned_text = '\n'.join(cleaned_lines)
        return cleaned_text, removed_segments
    
    def _is_repeated_line(self, line: str, all_lines: List[str]) -> bool:
        """Check if a line appears multiple times in the text (header/footer)."""
        if len(line) < 10:  # Too short to be meaningful
            return False
        
        count = sum(1 for l in all_lines if l.strip() == line)
        return count > 2  # Appears more than twice
    
    def _is_preserved_content(self, line: str, lines: List[str], index: int) -> bool:
        """Check if line is part of preserved content (table, list, code)."""
        line_stripped = line.strip()
        
        # Code block detection
        if line_stripped.startswith('```') or line_stripped.startswith('    ') or line_stripped.startswith('\t'):
            return True
        
        # List detection
        if re.match(r'^[\s]*[-*+]\s', line) or re.match(r'^[\s]*\d+\.\s', line):
            return True
        
        # Table detection (markdown or simple)
        if '|' in line and line.count('|') >= 2:
            return True
        
        # Warning/note detection
        if any(kw in line.lower() for kw in ['warning:', 'note:', 'caution:', 'important:', 'tip:']):
            return True
        
        # Heading detection
        if line_stripped.startswith('#'):
            return True
        
        return False
    
    def _apply_token_budget(
        self,
        chunks: List[Dict[str, Any]],
        token_budget: int,
    ) -> List[Dict[str, Any]]:
        """
        Apply token budget by truncating chunks from the end.
        
        Args:
            chunks: List of chunks
            token_budget: Maximum tokens allowed
            
        Returns:
            Truncated chunks
        """
        if token_budget <= 0:
            return chunks
        
        # Estimate tokens (rough: 4 chars per token)
        chars_per_token = 4.0
        max_chars = int(token_budget * chars_per_token)
        
        total_chars = sum(len(c.get("text", "") or c.get("content", "")) for c in chunks)
        
        if total_chars <= max_chars:
            return chunks
        
        # Truncate from the end
        current_chars = 0
        result = []
        
        for chunk in chunks:
            text = chunk.get("text", "") or chunk.get("content", "")
            if current_chars + len(text) > max_chars:
                remaining = max_chars - current_chars
                if remaining > 100:
                    chunk_copy = chunk.copy()
                    chunk_copy["text"] = text[:remaining] + "\n... [truncated due to token budget]"
                    chunk_copy["content"] = chunk_copy["text"]
                    result.append(chunk_copy)
                break
            result.append(chunk)
            current_chars += len(text)
        
        return result


# Global instance
chunk_compressor = ChunkCompressor({})