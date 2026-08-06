from typing import Optional, Dict, Any, List
from datetime import datetime
from app.services.retrieval.schemas import RetrievalFilters


class FilterBuilder:
    """Builds ChromaDB where clauses from retrieval filters."""

    # Mapping of filter fields to ChromaDB metadata keys
    FIELD_MAPPING = {
        "company": "company",
        "category": "category",
        "language": "language",
        "document_id": "document_id",
        "file_type": "file_type",
        "processing_status": "processing_status",
    }

    # Date fields that need special handling
    DATE_FIELDS = {
        "created_after": "created_at",
        "created_before": "created_at",
    }

    @classmethod
    def build_where_clause(cls, filters: RetrievalFilters) -> Optional[Dict[str, Any]]:
        """Build a ChromaDB where clause from retrieval filters."""
        conditions = []

        # Handle standard equality filters
        for filter_field, metadata_key in cls.FIELD_MAPPING.items():
            value = getattr(filters, filter_field, None)
            if value is not None:
                conditions.append({metadata_key: {"$eq": value}})

        # Handle date range filters
        if filters.created_after or filters.created_before:
            date_conditions = {}
            if filters.created_after:
                date_conditions["$gte"] = cls._format_datetime(filters.created_after)
            if filters.created_before:
                date_conditions["$lte"] = cls._format_datetime(filters.created_before)
            if date_conditions:
                conditions.append({"created_at": date_conditions})

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    @classmethod
    def _format_datetime(cls, dt: datetime) -> str:
        """Format datetime for ChromaDB query."""
        # ChromaDB expects ISO format strings
        return dt.isoformat()

    @classmethod
    def validate_filters(cls, filters: RetrievalFilters) -> List[str]:
        """Validate filters and return list of warnings/errors."""
        warnings = []

        # Check if document_id is valid UUID format
        if filters.document_id:
            try:
                from uuid import UUID
                UUID(filters.document_id)
            except ValueError:
                warnings.append(f"Invalid document_id format: {filters.document_id}")

        return warnings