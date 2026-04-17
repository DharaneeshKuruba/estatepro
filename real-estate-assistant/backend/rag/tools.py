"""
Five LangChain BaseTool subclasses for real estate Q&A.
Uses Groq (mixtral-8x7b-32768) as the LLM backend — no OpenAI key required.
"""
from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.rag.retriever import retrieve_documents
from backend.core.config import get_settings

settings = get_settings()


def _get_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.3,
    )


def _invoke_chain(chain, payload: dict, tool_name: str, user_role: str, agent_id: Optional[str]):
    """Invoke chain with LangSmith-friendly tags/metadata."""
    return chain.invoke(
        payload,
        config={
            "run_name": tool_name,
            "tags": ["estate-nexa", "tool", tool_name, f"role:{user_role}"],
            "metadata": {
                "tool": tool_name,
                "user_role": user_role,
                "agent_id": agent_id or "",
            },
        },
    )


def _format_context(docs: list[dict], user_role: str) -> str:
    """Build context string; strip actual price for buyers."""
    chunks = []
    for d in docs:
        content = d["content"]
        if user_role == "buyer":
            lines = [
                l for l in content.splitlines()
                if "actual price" not in l.lower() and "internal price" not in l.lower()
            ]
            content = "\n".join(lines)
        chunks.append(content)
    return "\n\n---\n\n".join(chunks) if chunks else "No relevant documents found."


def _augment_query_with_history(query: str, conversation_history: str) -> str:
    """
    Improve retrieval for follow-up questions like "above property", "that one", etc.
    """
    if not conversation_history.strip():
        return query

    lower_q = query.lower()
    followup_markers = [
        "above property",
        "that property",
        "this property",
        "that one",
        "this one",
        "same property",
        "selected property",
        "previous property",
        "details of above",
    ]
    if any(marker in lower_q for marker in followup_markers):
        history_tail = conversation_history[-1200:]
        return (
            f"{query}\n\n"
            f"Recent conversation context (for disambiguation only):\n{history_tail}"
        )

    return query


# ── Shared schema ──────────────────────────────────────────────────────────────
class ToolInput(BaseModel):
    query: str = Field(..., description="The user's question or search query.")
    user_role: str = Field(default="buyer", description="Role: admin | agent | buyer")
    agent_id: Optional[str] = Field(default=None, description="Agent's ID (agents only)")
    conversation_history: str = Field(
        default="",
        description="Recent chat history in the same session for follow-up resolution.",
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1. Property Retrieval
# ══════════════════════════════════════════════════════════════════════════════
class PropertyRetrievalTool(BaseTool):
    name: str = "property_retrieval"
    description: str = "Find and describe real estate property listings. Use this for any question about specific properties, their features, location, or pricing."
    args_schema: Type[BaseModel] = ToolInput

    def _run(
        self,
        query: str,
        user_role: str = "buyer",
        agent_id: Optional[str] = None,
        conversation_history: str = "",
    ) -> str:
        retrieval_query = _augment_query_with_history(query, conversation_history)
        docs = retrieve_documents(retrieval_query, tool="property_retrieval", user_role=user_role, agent_id=agent_id)
        context = _format_context(docs, user_role)
        price_note = (
            "You can show both quoted price and actual price."
            if user_role in ("admin", "agent")
            else "Show only quoted price. Do NOT mention actual or internal prices."
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an expert real estate property specialist.
Your job is to help users find and understand property listings.
{price_note}
Be specific, factual, and helpful.
Output in clean Markdown using:
## Overview
## Matching Properties
## Next Steps
Use '-' bullet lists where needed. Do not use decorative '**' around headings.
If the user asks a follow-up (e.g., "above property"), use conversation history to identify the exact property and answer specifically."""),
            ("human", "Conversation history:\n{conversation_history}\n\nContext:\n{context}\n\nQuestion: {query}"),
        ])
        chain = prompt | _get_llm() | StrOutputParser()
        return _invoke_chain(
            chain,
            {"conversation_history": conversation_history, "context": context, "query": query},
            self.name,
            user_role,
            agent_id,
        )

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError


# ══════════════════════════════════════════════════════════════════════════════
# 2. Summarization
# ══════════════════════════════════════════════════════════════════════════════
class SummarizationTool(BaseTool):
    name: str = "summarization"
    description: str = "Summarize property documents, legal agreements, or market reports. Use this when the user wants a concise overview or key points extracted."
    args_schema: Type[BaseModel] = ToolInput

    def _run(
        self,
        query: str,
        user_role: str = "buyer",
        agent_id: Optional[str] = None,
        conversation_history: str = "",
    ) -> str:
        # Retrieve from ALL document types — summarization can apply to any content
        retrieval_query = _augment_query_with_history(query, conversation_history)
        docs = retrieve_documents(retrieval_query, tool=None, user_role=user_role, agent_id=agent_id, n_results=6)
        context = _format_context(docs, user_role)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional real estate document analyst.
Provide clear, structured summaries in clean Markdown with headings (no decorative '**' around headings):
## Summary
## Key Highlights
## Legal or Financial Notes
## Conclusion
Use '-' bullet lists where needed.
- Keep wording concise and practical.
- Key highlights in bullet points
- Legal or financial clauses (if present) highlighted separately
- A brief conclusion
Use conversation history to resolve follow-up references precisely."""),
            ("human", "Conversation history:\n{conversation_history}\n\nDocument context:\n{context}\n\nSummarize for: {query}"),
        ])
        chain = prompt | _get_llm() | StrOutputParser()
        return _invoke_chain(
            chain,
            {"conversation_history": conversation_history, "context": context, "query": query},
            self.name,
            user_role,
            agent_id,
        )

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError



# ══════════════════════════════════════════════════════════════════════════════
# 3. Market Analysis
# ══════════════════════════════════════════════════════════════════════════════
class MarketAnalysisTool(BaseTool):
    name: str = "market_analysis"
    description: str = "Analyze real estate market trends, price movements, and regional insights. Use for market questions, investment climate, or area comparisons."
    args_schema: Type[BaseModel] = ToolInput

    def _run(
        self,
        query: str,
        user_role: str = "buyer",
        agent_id: Optional[str] = None,
        conversation_history: str = "",
    ) -> str:
        retrieval_query = _augment_query_with_history(query, conversation_history)
        docs = retrieve_documents(retrieval_query, tool="market_analysis", user_role=user_role, agent_id=agent_id)
        context = _format_context(docs, user_role)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior real estate market analyst with 15 years of experience.
Provide data-driven insights in clean Markdown with headings:
## Market Trends
## Supply and Demand
## Regional Comparison
## Outlook
Use '-' bullet lists where needed. Do not wrap headings with '**'.
- Current market trends and price movements
- Current market trends and price movements
- Supply and demand indicators
- Regional comparisons where relevant
- Future outlook based on available data
Use professional language and back claims with specific figures from the context.
Use conversation history to resolve follow-up references precisely."""),
            ("human", "Conversation history:\n{conversation_history}\n\nMarket data:\n{context}\n\nAnalysis request: {query}"),
        ])
        chain = prompt | _get_llm() | StrOutputParser()
        return _invoke_chain(
            chain,
            {"conversation_history": conversation_history, "context": context, "query": query},
            self.name,
            user_role,
            agent_id,
        )

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError


# ══════════════════════════════════════════════════════════════════════════════
# 4. Comparison
# ══════════════════════════════════════════════════════════════════════════════
class ComparisonTool(BaseTool):
    name: str = "comparison"
    description: str = "Compare multiple properties side-by-side. Use when the user wants to evaluate or choose between different options."
    args_schema: Type[BaseModel] = ToolInput

    def _run(
        self,
        query: str,
        user_role: str = "buyer",
        agent_id: Optional[str] = None,
        conversation_history: str = "",
    ) -> str:
        retrieval_query = _augment_query_with_history(query, conversation_history)
        docs = retrieve_documents(retrieval_query, tool="property_retrieval", user_role=user_role, agent_id=agent_id, n_results=8)
        context = _format_context(docs, user_role)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a real estate comparison specialist.
You must structure your response exactly with the following sections, ensuring you leave empty lines between headings, text, and table.
Do not wrap headings with decorative '**'.

### 1. Property Comparison

Format the main comparison as a Markdown table. Do NOT use bullet points or lists for this section.
Use exactly these columns in this order: Location | Price | Size | Bedrooms | Key Features | Pros | Cons
Use valid Markdown table syntax with a separator row (for example: |---|---|---|---|---|---|---|).

### 2. Detailed Analysis

Provide any extra comparative details if relevant, such as Rental Yield Comparison, Price per sqft, or ROI.

### 3. Recommendation

Give a brief recommendation based on the user's apparent needs.
Use conversation history to resolve follow-up references precisely."""),
            ("human", "Conversation history:\n{conversation_history}\n\nAvailable properties:\n{context}\n\nComparison request: {query}"),
        ])
        chain = prompt | _get_llm() | StrOutputParser()
        return _invoke_chain(
            chain,
            {"conversation_history": conversation_history, "context": context, "query": query},
            self.name,
            user_role,
            agent_id,
        )

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError


# ══════════════════════════════════════════════════════════════════════════════
# 5. Investment Recommendation
# ══════════════════════════════════════════════════════════════════════════════
class InvestmentRecommendationTool(BaseTool):
    name: str = "investment_recommendation"
    description: str = "Provide investment recommendations, ROI analysis, and risk assessment for properties. Use for investment strategy or buy/sell timing questions."
    args_schema: Type[BaseModel] = ToolInput

    def _run(
        self,
        query: str,
        user_role: str = "buyer",
        agent_id: Optional[str] = None,
        conversation_history: str = "",
    ) -> str:
        retrieval_query = _augment_query_with_history(query, conversation_history)
        docs = retrieve_documents(retrieval_query, tool="investment_recommendation", user_role=user_role, agent_id=agent_id)
        context = _format_context(docs, user_role)
        price_note = (
            "You have access to actual pricing data — use it for accurate ROI calculations."
            if user_role in ("admin", "agent")
            else "Use only publicly available pricing (quoted prices) for your analysis."
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a seasoned real estate investment advisor.
{price_note}
Structure your response in clean Markdown (no decorative '**' around headings):
## Top Recommendations
## ROI Estimate
## Risk Assessment
## Actionable Next Steps
Use '-' bullet lists where needed.
Use conversation history to resolve follow-up references precisely."""),
            ("human", "Conversation history:\n{conversation_history}\n\nInvestment data:\n{context}\n\nInvestment query: {query}"),
        ])
        chain = prompt | _get_llm() | StrOutputParser()
        return _invoke_chain(
            chain,
            {"conversation_history": conversation_history, "context": context, "query": query},
            self.name,
            user_role,
            agent_id,
        )

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError


# ── Tool registry ──────────────────────────────────────────────────────────────
_TOOL_MAP = {
    "property_retrieval":       PropertyRetrievalTool(),
    "summarization":            SummarizationTool(),
    "market_analysis":          MarketAnalysisTool(),
    "comparison":               ComparisonTool(),
    "investment_recommendation": InvestmentRecommendationTool(),
}


def run_tool(
    tool: str,
    query: str,
    user_role: str,
    agent_id: Optional[str] = None,
    conversation_history: str = "",
) -> str:
    """Dispatch to the appropriate tool by name."""
    t = _TOOL_MAP.get(tool)
    if not t:
        return f"Unknown tool: {tool}"
    try:
        return t._run(
            query=query,
            user_role=user_role,
            agent_id=agent_id,
            conversation_history=conversation_history,
        )
    except Exception as e:
        err = str(e)
        if "api_key" in err.lower() or "authentication" in err.lower() or "401" in err:
            return "⚠️ Groq API key is missing or invalid. Please add your GROQ_API_KEY to the .env file and restart the backend."
        return f"⚠️ Tool error: {err}"
