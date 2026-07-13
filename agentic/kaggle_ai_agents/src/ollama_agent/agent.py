"""Ollama agent with LangChain ReAct orchestration."""

from __future__ import annotations

import json

from langchain_ollama import ChatOllama
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

from src.base import Agent, NewsItem, DailyBrief
from src.ollama_agent.tools import discover, rank, validate


class OllamaAgent(Agent):
    """LangChain + Ollama ReAct agent."""

    def __init__(
        self,
        model: str = "qwen2.5-coder:14b",
        host: str = "http://localhost:11434",
        verbose: bool = True,
    ):
        """Initialize Ollama agent.
        
        Args:
            model: Ollama model name
            host: Ollama server URL
            verbose: Print agent thinking steps
        """
        self.model = model
        self.host = host
        self.verbose = verbose
        self.llm = None
        self.executor = None
        self._init_llm()
        self._init_agent()

    def _init_llm(self):
        """Initialize ChatOllama LLM."""
        self.llm = ChatOllama(
            model=self.model,
            base_url=self.host,
            temperature=0.7,
            top_k=40,
            top_p=0.9,
        )
        print(f"✅ Initialized ChatOllama: {self.model} @ {self.host}")

    def _init_agent(self):
        """Initialize ReAct agent with tools."""
        prompt = PromptTemplate.from_template(
            """You are an AI curator for AI/ML stories. Your task:
1. Use discover() to find recent stories
2. Use rank() to rank them by importance
3. Use validate() to finalize the brief

Think step-by-step. When ready, call validate() to complete.

Available tools: discover, rank, validate

{agent_scratchpad}"""
        )

        tools = [discover, rank, validate]

        agent = create_react_agent(self.llm, tools, prompt)

        self.executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=self.verbose,
            max_iterations=10,
            handle_parsing_errors=True,
        )
        print(f"✅ Initialized AgentExecutor with ReAct pattern")

    def discover(self) -> list[NewsItem]:
        """Not used directly; called via tool."""
        raise NotImplementedError("Use run() to execute full pipeline")

    def rank(self, items, count: int = 10):
        """Not used directly; called via tool."""
        raise NotImplementedError("Use run() to execute full pipeline")

    def validate(self, items) -> DailyBrief:
        """Not used directly; called via tool."""
        raise NotImplementedError("Use run() to execute full pipeline")

    def run(self) -> DailyBrief:
        """Execute full pipeline via LangChain AgentExecutor.
        
        Returns:
            DailyBrief with 10 ranked stories
        """
        print("\n[LangChain Agent Loop]")

        result = self.executor.invoke(
            {"input": "Generate a top-10 AI/ML stories brief for today."}
        )

        # Extract DailyBrief from output
        output_text = result.get("output", "")
        
        try:
            # Try to parse as JSON
            if output_text.startswith("{"):
                brief_dict = json.loads(output_text)
            else:
                # Fallback: extract JSON from text
                import re
                match = re.search(r"\{.*\}", output_text, re.DOTALL)
                if match:
                    brief_dict = json.loads(match.group(0))
                else:
                    raise ValueError("Could not extract JSON from output")
            
            brief = DailyBrief(**brief_dict)
            print(f"✅ Brief generated: {len(brief.cards)} cards")
            return brief

        except Exception as e:
            print(f"❌ Error parsing brief: {str(e)[:100]}")
            raise
