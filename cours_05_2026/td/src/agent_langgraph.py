import json
import operator
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import Annotated, TypedDict

from src.llm_openai import OpenAIConfig
from src.memory import PersistentMemoryStore
from src.rag_store import RAGStore
from src.tools import ToolConfig, get_tools

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------


@dataclass
class AgentConfig:
    trace: bool = False


# -------------------------------------------------------------------
# State
# -------------------------------------------------------------------


class AgentState(TypedDict):
    """
    Structuration basique de l'état de l'agent :
    - les messages de l'historique
    - le nombre de tool calls passé
    - le nombre maximum de tool calls autorisé
    """

    messages: Annotated[List[AnyMessage], operator.add]
    tool_calls_count: int
    max_tool_calls: int


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------


class FileAgentLangGraph:
    def __init__(
        self,
        tool_cfg: ToolConfig,
        llm_cfg: OpenAIConfig,
        rag_store: Optional[RAGStore] = None,
        memory_store: Optional[PersistentMemoryStore] = None,
        agent_cfg: Optional[AgentConfig] = None,
    ) -> None:
        self.tool_cfg = tool_cfg
        self.llm_cfg = llm_cfg
        self.rag_store = rag_store
        self.memory_store = memory_store
        self.cfg = agent_cfg or AgentConfig()

        # Historique conservé entre tours, comme dans les autres agents
        # qu'on a codés jusqu'ici.
        self.history: List[AnyMessage] = []

        # Tools "maison" déjà existants (on ne fait pas exotique ici)
        self.file_tools = get_tools(cfg=self.tool_cfg)

        # Outils LangChain exposés au modèle
        self.tools = self._build_langchain_tools()

        # Modèle avec tool calling natif
        self.model = ChatOpenAI(
            model=self.llm_cfg.model,
            temperature=self.llm_cfg.temperature,
            timeout=self.llm_cfg.timeout_s,
        ).bind_tools(self.tools)

        # Graphe compilé
        self.graph = self._build_graph()

    # ---------------------------------------------------------------
    # Methodes de classe (API)
    # ---------------------------------------------------------------

    def reset(self) -> None:
        self.history = []

    def set_trace(self, enabled: bool) -> None:
        self.cfg.trace = enabled

    def run(self, user_input: str) -> str:
        initial_state: AgentState = {
            "messages": self.history + [HumanMessage(content=user_input)],
            "tool_calls_count": 0,
        }

        final_state = self.graph.invoke(initial_state)

        # On garde l'historique complet pour le prochain tour
        self.history = final_state["messages"]

        # On récupère le dernier message "assistant" non tool-call
        final_text = self._extract_final_answer(final_state["messages"])
        return final_text

    # ---------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------

    def _log(self, msg: str) -> None:
        if self.cfg.trace:
            print(f"[trace] {msg}")

    def _system_prompt(self) -> str:
        base = """
You are a careful local file assistant.

You can use tools to inspect local files and optionally:
- retrieve indexed document chunks
- search persistent memory
- write durable notes to persistent memory

Rules:
- Only use tools when needed.
- Prefer short, precise tool arguments.
- Never invent file contents.
- If exact evidence is needed, use tools first.
- Be concise and factual.
""".strip()

        if self.rag_store is not None:
            base += "\n- A retrieval tool is available for indexed documents."
        if self.memory_store is not None:
            base += "\n- Persistent memory tools are available, but store only durable, useful facts."

        return base

    def _extract_final_answer(self, messages: List[AnyMessage]) -> str:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                if not getattr(msg, "tool_calls", None):
                    content = msg.content
                    if isinstance(content, str) and content.strip():
                        return content.strip()
        return "No final answer produced."

    def _build_langchain_tools(self):
        # --- file tools ---

        @tool
        def list_dir(path: str) -> str:
            """List files and folders inside a directory relative to BASE_DIR."""
            result = self.file_tools["list_dir"](path=path)
            return json.dumps(result, ensure_ascii=False)

        @tool
        def read_file(path: str, max_bytes: Optional[int] = None) -> str:
            """Read a text file relative to BASE_DIR."""
            kwargs = {"path": path}
            if max_bytes is not None:
                kwargs["max_bytes"] = max_bytes
            result = self.file_tools["read_file"](**kwargs)
            return json.dumps(result, ensure_ascii=False)

        @tool
        def search_in_files(path: str, query: str, max_matches: int = 50) -> str:
            """Search for a short query string inside text files under a directory."""
            result = self.file_tools["search_in_files"](
                path=path,
                query=query,
                max_matches=max_matches,
            )
            return json.dumps(result, ensure_ascii=False)

        tools = [list_dir, read_file, search_in_files]

        # --- optional RAG tool ---

        if self.rag_store is not None:

            @tool
            def retrieve_documents(query: str, top_k: int = 4) -> str:
                """Retrieve top relevant document chunks from the indexed document store."""
                result = self.rag_store.retrieve(query=query, top_k=top_k)
                return json.dumps(result, ensure_ascii=False)

            tools.append(retrieve_documents)

        # --- optional memory tools ---

        if self.memory_store is not None:

            @tool
            def search_memory(query: str, top_k: int = 3) -> str:
                """Search persistent memory for prior useful notes."""
                result = self.memory_store.search(query=query, top_k=top_k)
                return json.dumps(result, ensure_ascii=False)

            @tool
            def remember_note(
                text: str, kind: str = "episodic", source: str = "agent"
            ) -> str:
                """Store a durable note in persistent memory."""
                result = self.memory_store.append(text=text, kind=kind, source=source)
                return json.dumps(result, ensure_ascii=False)

            tools.extend([search_memory, remember_note])

        return tools

    # ---------------------------------------------------------------
    # Graph definition
    # ---------------------------------------------------------------

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("call_model", self._call_model)
        graph.add_node("execute_tools", self._execute_tools)
        graph.add_node("too_many_tools", self._too_many_tools)

        graph.add_edge(START, "call_model")
        graph.add_conditional_edges(
            "call_model",
            self._route_after_model,
            {
                "tools": "execute_tools",
                "final": END,
                "too_many_tools": "too_many_tools",
            },
        )
        graph.add_edge("execute_tools", "call_model")
        graph.add_edge("too_many_tools", END)

        return graph.compile()

    # ---------------------------------------------------------------
    # Nodes
    # ---------------------------------------------------------------

    def _call_model(self, state: AgentState) -> Dict[str, Any]:
        self._log(
            f"call_model | messages={len(state['messages'])} | tool_calls_count={state['tool_calls_count']}"
        )

        response = self.model.invoke(
            [SystemMessage(content=self._system_prompt())] + state["messages"]
        )

        self._log(
            f"model returned | tool_calls={len(getattr(response, 'tool_calls', []) or [])}"
        )

        return {"messages": [response]}

    def _execute_tools(self, state: AgentState) -> Dict[str, Any]:
        last_msg = state["messages"][-1]

        if not isinstance(last_msg, AIMessage):
            return {}

        tool_messages: List[ToolMessage] = []
        tool_calls = getattr(last_msg, "tool_calls", []) or []

        for tc in tool_calls:
            tool_name = tc["name"]
            args = tc.get("args", {}) or {}
            tool_call_id = tc["id"]

            self._log(f"execute_tools | {tool_name} args={args}")

            tool_obj = next((t for t in self.tools if t.name == tool_name), None)

            if tool_obj is None:
                result = json.dumps(
                    {"ok": False, "error": f"Unknown tool: {tool_name}"},
                    ensure_ascii=False,
                )
            else:
                try:
                    raw_result = tool_obj.invoke(args)
                    result = (
                        raw_result
                        if isinstance(raw_result, str)
                        else json.dumps(raw_result, ensure_ascii=False)
                    )
                except Exception as e:
                    result = json.dumps(
                        {"ok": False, "error": str(e)}, ensure_ascii=False
                    )

            self._log(f"tool result | {tool_name} -> {result[:300]}")

            tool_messages.append(
                ToolMessage(
                    content=result,
                    tool_call_id=tool_call_id,
                )
            )

        return {
            "messages": tool_messages,
            "tool_calls_count": state["tool_calls_count"] + len(tool_calls),
        }

    def _too_many_tools(self, state: AgentState) -> Dict[str, Any]:
        self._log("too_many_tools | stopping graph")
        return {
            "messages": [
                AIMessage(
                    content="Stopping because the maximum number of tool calls was reached."
                )
            ]
        }

    # ---------------------------------------------------------------
    # Edges
    # ---------------------------------------------------------------

    def _route_after_model(self, state: AgentState) -> str:
        last_msg = state["messages"][-1]

        if not isinstance(last_msg, AIMessage):
            return "final"

        tool_calls = getattr(last_msg, "tool_calls", []) or []

        if not tool_calls:
            return "final"

        return "tools"
