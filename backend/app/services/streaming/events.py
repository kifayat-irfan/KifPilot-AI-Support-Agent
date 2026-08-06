import json
from typing import Any, Dict, Optional
from app.services.streaming.schemas import (
    StreamStartEvent,
    StreamRetrievalEvent,
    StreamTokenEvent,
    StreamCitationsEvent,
    StreamCompleteEvent,
    StreamErrorEvent,
    StreamEvent,
)


class SSEFormatter:
    """Formats events as Server-Sent Events (SSE)."""
    
    @staticmethod
    def format_event(event: StreamEvent) -> str:
        """Format a stream event as SSE.
        
        Args:
            event: The event to format
            
        Returns:
            SSE-formatted string
        """
        event_data = event.model_dump(exclude_none=True)
        event_type = event_data.pop("event", "message")
        
        lines = [f"event: {event_type}"]
        lines.append(f"data: {json.dumps(event_data)}")
        lines.append("")  # Empty line to separate events
        
        return "\n".join(lines)
    
    @staticmethod
    def format_start() -> str:
        """Format start event."""
        event = StreamStartEvent()
        return SSEFormatter.format_event(event)
    
    @staticmethod
    def format_retrieval(chunks_found: int, search_time_ms: float) -> str:
        """Format retrieval event."""
        event = StreamRetrievalEvent(
            chunks_found=chunks_found,
            search_time_ms=search_time_ms
        )
        return SSEFormatter.format_event(event)
    
    @staticmethod
    def format_token(text: str) -> str:
        """Format token event."""
        event = StreamTokenEvent(text=text)
        return SSEFormatter.format_event(event)
    
    @staticmethod
    def format_citations(citations: list) -> str:
        """Format citations event."""
        event = StreamCitationsEvent(citations=citations)
        return SSEFormatter.format_event(event)
    
    @staticmethod
    def format_complete(confidence: float, sources_found: int, response_time_ms: float) -> str:
        """Format completion event."""
        event = StreamCompleteEvent(
            confidence=confidence,
            sources_found=sources_found,
            response_time_ms=response_time_ms
        )
        return SSEFormatter.format_event(event)
    
    @staticmethod
    def format_error(error: str, code: str = "STREAMING_ERROR") -> str:
        """Format error event."""
        event = StreamErrorEvent(error=error, code=code)
        return SSEFormatter.format_event(event)
    
    @staticmethod
    def format_heartbeat() -> str:
        """Format a heartbeat comment to keep connection alive."""
        return ": heartbeat\n\n"


class SSEParser:
    """Utility for parsing SSE events (for testing)."""
    
    @staticmethod
    def parse_events(sse_data: str) -> list:
        """Parse SSE data into events."""
        events = []
        lines = sse_data.strip().split("\n")
        current_event = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_event:
                    events.append(current_event)
                    current_event = {}
                continue
            
            if line.startswith("event:"):
                current_event["event"] = line[6:].strip()
            elif line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    current_event["data"] = json.loads(data_str)
                except json.JSONDecodeError:
                    current_event["data"] = data_str
        
        if current_event:
            events.append(current_event)
        
        return events