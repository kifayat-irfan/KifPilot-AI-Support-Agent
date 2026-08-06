from typing import List, Dict, Any
from app.services.rag.schemas import RAGSource
from app.core.config import get_settings

settings = get_settings()


class PromptBuilder:
    """Builds prompts for RAG answer generation."""

    SYSTEM_PROMPT = """You are an enterprise knowledge assistant. Your role is to answer questions using ONLY the supplied context from the company's indexed documentation.

CRITICAL RULES:
1. Answer ONLY using the supplied context. Never use outside knowledge.
2. If the answer cannot be found inside the provided context, reply EXACTLY: "I cannot find this information in the indexed documentation."
3. Never invent facts, figures, or details not present in the context.
4. Do not speculate or make assumptions beyond what is explicitly stated.
5. If the context contains conflicting information, acknowledge the conflict and present both viewpoints.
6. Keep answers concise and focused on the question asked.

CONTEXT FORMAT:
The context contains chunks from indexed documents. Each chunk includes:
- Document name
- Page number (if available)
- Section heading (if available)
- The text content

When referencing information, mention the document name and page/section when relevant."""

    @classmethod
    def build_prompt(cls, question: str, context: str) -> List[Dict[str, str]]:
        """
        Build the complete prompt for the LLM.
        
        Args:
            question: User's question
            context: Retrieved and formatted context
            
        Returns:
            List of message dictionaries for chat completion
        """
        user_prompt = f"""CONTEXT:
{context}

QUESTION:
{question}

Answer the question using ONLY the context above. If the information is not in the context, respond exactly: "I cannot find this information in the indexed documentation.\""""

        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    @classmethod
    def build_prompt_with_sources(cls, question: str, context: str, sources: List[RAGSource]) -> List[Dict[str, str]]:
        """
        Build prompt with explicit source attribution.
        
        Args:
            question: User's question
            context: Retrieved and formatted context
            sources: List of source documents
            
        Returns:
            List of message dictionaries for chat completion
        """
        # Build source reference section
        source_refs = []
        for i, source in enumerate(sources, 1):
            ref = f"[{i}] {source.document_name}"
            if source.page:
                ref += f", page {source.page}"
            if source.section:
                ref += f", section: {source.section}"
            source_refs.append(ref)
        
        sources_text = "\n".join(source_refs) if source_refs else "No sources available"

        user_prompt = f"""CONTEXT:
{context}

SOURCES:
{sources_text}

QUESTION:
{question}

Answer the question using ONLY the context above. If the information is not in the context, respond exactly: "I cannot find this information in the indexed documentation.\""""

        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    @classmethod
    def build_prompt_with_sources_and_history(
        cls,
        question: str,
        context: str,
        sources: List[RAGSource],
        conversation_history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Build prompt with explicit source attribution and conversation history.
        
        Args:
            question: User's question
            context: Retrieved and formatted context
            sources: List of source documents
            conversation_history: Previous conversation messages
            
        Returns:
            List of message dictionaries for chat completion
        """
        # Build source reference section
        source_refs = []
        for i, source in enumerate(sources, 1):
            ref = f"[{i}] {source.document_name}"
            if source.page:
                ref += f", page {source.page}"
            if source.section:
                ref += f", section: {source.section}"
            source_refs.append(ref)
        
        sources_text = "\n".join(source_refs) if source_refs else "No sources available"

        # Build conversation history section
        history_text = ""
        if conversation_history:
            history_lines = []
            for msg in conversation_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "system":
                    continue  # System prompt is handled separately
                history_lines.append(f"{role.upper()}: {content}")
            if history_lines:
                history_text = "\n\nCONVERSATION HISTORY:\n" + "\n".join(history_lines)

        user_prompt = f"""CONTEXT:
{context}

SOURCES:
{sources_text}
{history_text}

QUESTION:
{question}

Answer the question using ONLY the context above. If the information is not in the context, respond exactly: "I cannot find this information in the indexed documentation.\""""

        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]