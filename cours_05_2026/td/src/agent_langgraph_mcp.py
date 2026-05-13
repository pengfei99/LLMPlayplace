import json
import operator
import time
from dataclasses import dataclass
from pathlib import Path
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
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing_extensions import Annotated, TypedDict

from src.llm_openai import OpenAIConfig
from src.memory import PersistentMemoryStore
from src.rag_store import RAGStore
from src.schemas import FinalAnswer
from src.tools_advanced import ToolConfig, get_tools


@dataclass
class AgentConfig:
    max_tool_calls: int = 5
    timeout_s: int = 30
    trace: bool = False
    log_path: str = ".agent_trace.jsonl"
    interrupt_on_tools: Optional[set[str]] = None


class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    tool_calls_count: int
    max_tool_calls: int
    started_at: float
    audit_log: Annotated[List[Dict[str, Any]], operator.add]
    visited_files: Annotated[List[str], operator.add]
    last_tool_name: str
    pending_tool_call: Dict[str, Any]
    final_response: Dict[str, Any]
    last_tool_signature: str
    repeated_tool_calls: int


class FileAgentLangGraphMCP:
    def __init__(
        self,
        tool_cfg: ToolConfig,
        llm_cfg: OpenAIConfig,
        rag_store: Optional[RAGStore] = None,
        memory_store: Optional[PersistentMemoryStore] = None,
        agent_cfg: Optional[AgentConfig] = None,
        extra_tools: Optional[List[Any]] = None,
    ) -> None:
        self.tool_cfg = tool_cfg
        self.llm_cfg = llm_cfg
        self.rag_store = rag_store
        self.memory_store = memory_store
        self.cfg = agent_cfg or AgentConfig()
        self.history: List[AnyMessage] = []
        self.extra_tools = extra_tools or []

        self.file_tools = get_tools(cfg=self.tool_cfg)
        self.tools = self._build_langchain_tools()
        self._log(f"Available tools: {[t.name for t in self.tools]}")

        self.model = ChatOpenAI(
            model=self.llm_cfg.model,
            temperature=self.llm_cfg.temperature,
            timeout=self.llm_cfg.timeout_s,
        ).bind_tools(self.tools)

        # second model call only for schema-validated final answer
        self.final_model = ChatOpenAI(
            model=self.llm_cfg.model,
            temperature=0.0,
            timeout=self.llm_cfg.timeout_s,
        ).with_structured_output(FinalAnswer)

        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    # ---------------------------------------------------------------
    # public API
    # ---------------------------------------------------------------

    def reset(self) -> None:
        self.history = []

    def set_trace(self, enabled: bool) -> None:
        self.cfg.trace = enabled

    def run(self, user_input: str, thread_id: str = "default") -> str:
        initial_state: AgentState = {
            "messages": self.history + [HumanMessage(content=user_input)],
            "tool_calls_count": 0,
            "max_tool_calls": self.cfg.max_tool_calls,
            "started_at": time.time(),
            "audit_log": [],
            "visited_files": [],
            "last_tool_name": "",
            "pending_tool_call": {},
            "final_response": {},
            "last_tool_signature": "",
            "repeated_tool_calls": 0,
        }

        config = {"configurable": {"thread_id": thread_id}}

        result = self.graph.invoke(initial_state, config=config)

        if "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            return f"[HITL REQUIRED] {json.dumps(payload, ensure_ascii=False)}"

        self.history = self._conversation_only_history(
            result["messages"], keep_last_turns=6
        )

        final_response = result.get("final_response", {})
        if isinstance(final_response, dict) and final_response.get("answer"):
            return final_response["answer"]

        return self._extract_last_ai_message(result["messages"])

    def resume_after_human_decision(
        self,
        decision: Dict[str, Any],
        thread_id: str = "default",
    ) -> str:
        config = {"configurable": {"thread_id": thread_id}}
        result = self.graph.invoke(Command(resume=decision), config=config)

        if "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            return f"[HITL REQUIRED] {json.dumps(payload, ensure_ascii=False)}"

        self.history = self._conversation_only_history(
            result["messages"], keep_last_turns=6
        )
        final_response = result.get("final_response", {})
        if isinstance(final_response, dict) and final_response.get("answer"):
            return final_response["answer"]

        return self._extract_last_ai_message(result["messages"])

    # ---------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------

    def _log(self, msg: str) -> None:
        if self.cfg.trace:
            print(f"[trace] {msg}")

    def _append_jsonl(self, record: Dict[str, Any]) -> None:
        path = Path(self.cfg.log_path)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _system_prompt(self) -> str:
        return """
        You are a careful assistant with access to external MCP tools.

        Your job is to answer questions using the available MCP tools when needed.

        Rules:
        - For weather, forecast, temperature, rain, wind, or air quality questions, use the MCP weather tools.
        - After getting a useful tool result, answer directly.
        - Do not repeat the same tool call with the same arguments if it already failed or returned no useful information.
        - If a tool returns an error, explain the error briefly instead of retrying indefinitely.
        - Keep answers short and factual.
        """.strip()

    def _extract_last_ai_message(self, messages: List[AnyMessage]) -> str:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                if isinstance(msg.content, str) and msg.content.strip():
                    return msg.content.strip()
        return "No answer produced."

    def _conversation_only_history(
        self, messages: List[AnyMessage], keep_last_turns: int = 6
    ) -> List[AnyMessage]:
        """
        Ne garde que l'historique conversationnel entre tours :
        - HumanMessage
        - AIMessage finaux (sans tool_calls)

        On jette les AIMessage intermédiaires avec tool_calls
        et tous les ToolMessage.
        """
        cleaned: List[AnyMessage] = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                cleaned.append(msg)
            elif isinstance(msg, AIMessage):
                tool_calls = getattr(msg, "tool_calls", None)
                if not tool_calls:
                    cleaned.append(msg)

        # garde seulement les derniers tours
        return cleaned[-(2 * keep_last_turns) :]

    def _trim_messages(
        self,
        messages: List[AnyMessage],
        keep_last_turns: int = 4,
        max_tool_content_chars: int = 800,
    ) -> List[AnyMessage]:
        """
        Garde les derniers tours complets sans casser la structure :
        - HumanMessage
        - AIMessage final
        - AIMessage(tool_calls) + ToolMessage associés

        On parcourt depuis la fin et on reconstruit des blocs valides.
        """
        if not messages:
            return messages

        selected_blocks: List[List[AnyMessage]] = []
        i = len(messages) - 1
        human_count = 0

        while i >= 0 and human_count < keep_last_turns:
            msg = messages[i]

            # Cas 1. ToolMessage(s) en fin de bloc
            if isinstance(msg, ToolMessage):
                tool_block = [msg]
                i -= 1

                while i >= 0 and isinstance(messages[i], ToolMessage):
                    tool_block.insert(0, messages[i])
                    i -= 1

                # Le message précédent doit être l'AIMessage qui a émis les tool_calls
                if i >= 0 and isinstance(messages[i], AIMessage):
                    ai_msg = messages[i]
                    selected_blocks.insert(0, [ai_msg] + tool_block)
                    i -= 1
                else:
                    # Cas incohérent, on garde quand même les tool messages
                    selected_blocks.insert(0, tool_block)

                continue

            # Cas 2. AIMessage final simple
            if isinstance(msg, AIMessage):
                selected_blocks.insert(0, [msg])
                i -= 1
                continue

            # Cas 3. HumanMessage
            if isinstance(msg, HumanMessage):
                selected_blocks.insert(0, [msg])
                human_count += 1
                i -= 1
                continue

            # Cas 4. autres messages éventuels
            selected_blocks.insert(0, [msg])
            i -= 1

        # Re-flatten
        trimmed: List[AnyMessage] = []
        for block in selected_blocks:
            for msg in block:
                if isinstance(msg, ToolMessage):
                    content = msg.content
                    if not isinstance(content, str):
                        content = str(content)
                    content = self._compress_tool_content(
                        content,
                        max_chars=max_tool_content_chars,
                    )
                    trimmed.append(
                        ToolMessage(
                            content=content,
                            tool_call_id=msg.tool_call_id,
                        )
                    )
                else:
                    trimmed.append(msg)

        return trimmed

    def _compress_tool_content(self, text: str, max_chars: int = 2000) -> str:
        if not isinstance(text, str):
            text = str(text)
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...[truncated]..."

    # ---------------------------------------------------------------
    # Checkpointing
    # ---------------------------------------------------------------

    def list_checkpoints(
        self, thread_id: str = "default", finals_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retourne une liste lisible de checkpoints pour un thread.
        Par défaut, on ne montre que les checkpoints "finaux" du tour
        (ceux où next == ()), pour éviter d'exposer tous les super-steps.
        """
        config = {"configurable": {"thread_id": thread_id}}
        history = list(self.graph.get_state_history(config))

        out: List[Dict[str, Any]] = []
        for snap in history:
            is_final = tuple(snap.next) == ()
            if finals_only and not is_final:
                continue

            values = snap.values or {}
            messages = values.get("messages", [])
            preview = ""

            # essaie d'extraire la dernière réponse assistant lisible
            for msg in reversed(messages):
                content = getattr(msg, "content", None)
                if isinstance(content, str) and content.strip():
                    preview = content.strip().replace("\n", " ")[:120]
                    break

            out.append(
                {
                    "checkpoint_id": snap.config["configurable"]["checkpoint_id"],
                    "created_at": snap.created_at,
                    "step": snap.metadata.get("step"),
                    "source": snap.metadata.get("source"),
                    "is_final": is_final,
                    "next": list(snap.next),
                    "preview": preview,
                }
            )

        return out

    def replay_from_checkpoint(
        self, checkpoint_id: str, thread_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Rejoue le graphe à partir d'un checkpoint antérieur.
        LangGraph saute les nœuds avant le checkpoint et réexécute ceux après.
        """
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }

        result = self.graph.invoke(None, config=config)

        if "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            return f"[HITL REQUIRED] {json.dumps(payload, ensure_ascii=False)}"

        self.history = self._conversation_only_history(
            result["messages"], keep_last_turns=6
        )

        final_response = result.get("final_response", {})
        if isinstance(final_response, dict) and final_response.get("answer"):
            return final_response["answer"]

        return self._extract_last_ai_message(result["messages"])

    def get_checkpoint_state(
        self, checkpoint_id: str, thread_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Retourne un résumé du state pour un checkpoint précis.
        Utile pour inspection avant replay.
        """
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }

        snap = self.graph.get_state(config)

        values = snap.values or {}
        return {
            "checkpoint_id": snap.config["configurable"]["checkpoint_id"],
            "created_at": snap.created_at,
            "step": snap.metadata.get("step"),
            "source": snap.metadata.get("source"),
            "next": list(snap.next),
            "keys": sorted(values.keys()),
            "visited_files": values.get("visited_files", []),
            "tool_calls_count": values.get("tool_calls_count", 0),
        }

    # ---------------------------------------------------------------
    # tools
    # ---------------------------------------------------------------

    def _build_langchain_tools(self):
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
            """Search for a short string inside text files under a directory."""
            result = self.file_tools["search_in_files"](
                path=path, query=query, max_matches=max_matches
            )
            return json.dumps(result, ensure_ascii=False)

        @tool
        def write_text_file(path: str, content: str, overwrite: bool = False) -> str:
            """Write a text file inside outputs/ relative to BASE_DIR."""
            result = self.file_tools["write_text_file"](
                path=path,
                content=content,
                overwrite=overwrite,
            )
            return json.dumps(result, ensure_ascii=False)

        tools = [list_dir, read_file, search_in_files, write_text_file]

        if self.rag_store is not None:

            @tool
            def retrieve_documents(query: str, top_k: int = 4) -> str:
                """Retrieve top relevant chunks from the indexed document store."""
                result = self.rag_store.retrieve(query=query, top_k=top_k)
                return json.dumps(result, ensure_ascii=False)

            tools.append(retrieve_documents)

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

        tools.extend(self.extra_tools)

        return tools

    # ---------------------------------------------------------------
    # graph
    # ---------------------------------------------------------------

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("call_model", self._call_model)
        graph.add_node("human_review", self._human_review)
        graph.add_node("execute_tools", self._execute_tools)
        graph.add_node("format_final", self._format_final)
        graph.add_node("stop_with_error", self._stop_with_error)

        graph.add_edge(START, "call_model")

        graph.add_conditional_edges(
            "call_model",
            self._route_after_model,
            {
                "tools": "human_review",
                "final": "format_final",
                "stop": "stop_with_error",
            },
        )

        graph.add_conditional_edges(
            "human_review",
            self._route_after_human_review,
            {
                "execute": "execute_tools",
                "skip": "call_model",
                "stop": "stop_with_error",
            },
        )

        graph.add_edge("execute_tools", "call_model")
        graph.add_edge("format_final", END)
        graph.add_edge("stop_with_error", END)

        return graph.compile(checkpointer=self.checkpointer)

    # ---------------------------------------------------------------
    # nodes
    # ---------------------------------------------------------------

    def _call_model(self, state: AgentState) -> Dict[str, Any]:
        started_at = state.get("started_at", time.time())
        elapsed = time.time() - started_at
        if elapsed > self.cfg.timeout_s:
            return {
                "audit_log": [
                    {
                        "event": "timeout",
                        "elapsed_s": round(elapsed, 3),
                    }
                ]
            }

        trimmed_messages = self._trim_messages(
            state["messages"],
            keep_last_turns=4,
            max_tool_content_chars=800,
        )

        prompt_messages = [SystemMessage(content=self._system_prompt())]

        try:
            self._log(
                f"call_model | messages={len(state['messages'])} | tool_calls={state['tool_calls_count']}"
            )
        except:
            self._log(f"call_model | messages={len(state['messages'])}")

        if state.get("session_summary"):
            prompt_messages.append(
                SystemMessage(
                    content=f"Session summary of earlier context:\n{state['session_summary']}"
                )
            )

        response = self.model.invoke(prompt_messages + trimmed_messages)

        event = {
            "event": "model_output",
            "tool_calls": getattr(response, "tool_calls", []) or [],
            "content_preview": response.content[:300]
            if isinstance(response.content, str)
            else "",
        }
        self._append_jsonl(event)

        return {
            "messages": [response],
            "audit_log": [event],
            "started_at": started_at,
        }

    def _human_review(self, state: AgentState) -> Dict[str, Any]:
        last_msg = state["messages"][-1]
        if not isinstance(last_msg, AIMessage):
            return {}

        tool_calls = getattr(last_msg, "tool_calls", []) or []
        if not tool_calls:
            return {}

        first = tool_calls[0]
        tool_name = first["name"]
        args = first.get("args", {}) or {}

        if (
            not self.cfg.interrupt_on_tools
            or tool_name not in self.cfg.interrupt_on_tools
        ):
            return {
                "pending_tool_call": {
                    "decision": "approve",
                    "tool_name": tool_name,
                    "args": args,
                }
            }

        if tool_name == "write_text_file":
            content = args.get("content", "")
            preview_lines = content.splitlines()[:12]
            payload = {
                "question": "Approve file write?",
                "tool_name": tool_name,
                "path": args.get("path"),
                "overwrite": args.get("overwrite", False),
                "content_preview": "\n".join(preview_lines),
                "content_chars": len(content),
                "allowed_decisions": ["approve", "reject"],
            }
        else:
            payload = {
                "question": "Approve this tool call?",
                "tool_name": tool_name,
                "args": args,
                "allowed_decisions": ["approve", "reject"],
            }

        decision = interrupt(payload)

        return {
            "pending_tool_call": {
                "decision": decision.get("decision", "reject"),
                "tool_name": tool_name,
                "args": args,
            },
            "audit_log": [
                {
                    "event": "human_review",
                    "payload": payload,
                    "decision": decision,
                }
            ],
        }

    def _execute_tools(self, state: AgentState) -> Dict[str, Any]:
        last_msg = state["messages"][-1]
        if not isinstance(last_msg, AIMessage):
            return {}

        pending = state.get("pending_tool_call", {}) or {}
        decision = pending.get("decision", "approve")

        if decision != "approve":
            tool_messages: List[ToolMessage] = []
            for tc in last_msg.tool_calls:
                tool_messages.append(
                    ToolMessage(
                        content=json.dumps(
                            {"ok": False, "error": "Tool call rejected by human"},
                            ensure_ascii=False,
                        ),
                        tool_call_id=tc["id"],
                    )
                )
            event = {
                "event": "tool_rejected",
                "tool_name": pending.get("tool_name", ""),
            }
            self._append_jsonl(event)
            return {
                "messages": tool_messages,
                "audit_log": [event],
            }

        tool_messages: List[ToolMessage] = []
        visited_files: List[str] = []
        audit_records: List[Dict[str, Any]] = []

        for tc in last_msg.tool_calls:
            tool_name = tc["name"]
            args = tc.get("args", {}) or {}
            tool_call_id = tc["id"]

            current_signature = json.dumps(
                {"tool_name": tool_name, "args": args},
                sort_keys=True,
                ensure_ascii=False,
            )

            previous_signature = state.get("last_tool_signature", "")
            repeated_count = state.get("repeated_tool_calls", 0)

            if current_signature == previous_signature:
                repeated_count += 1
            else:
                repeated_count = 0

            tool_obj = next((t for t in self.tools if t.name == tool_name), None)
            if tool_obj is None:
                result = json.dumps(
                    {"ok": False, "error": f"Unknown tool: {tool_name}"},
                    ensure_ascii=False,
                )
            else:
                if repeated_count >= 2:
                    result = json.dumps(
                        {
                            "ok": False,
                            "error": "Refused: repeated identical tool call loop detected",
                        },
                        ensure_ascii=False,
                    )
                else:
                    try:
                        # MCP tools loaded via langchain-mcp-adapters are often async-only.
                        # Local Python tools still support normal sync invoke().
                        if hasattr(tool_obj, "ainvoke"):
                            try:
                                import asyncio

                                raw_result = asyncio.run(tool_obj.ainvoke(args))
                            except RuntimeError:
                                # Fallback in case an event loop is already running.
                                result = json.dumps(
                                    {
                                        "ok": False,
                                        "error": "Async MCP tool requires an awaitable execution context",
                                    },
                                    ensure_ascii=False,
                                )
                                raw_result = None
                        else:
                            raw_result = tool_obj.invoke(args)

                        if raw_result is not None:
                            result = (
                                raw_result
                                if isinstance(raw_result, str)
                                else json.dumps(raw_result, ensure_ascii=False)
                            )

                    except Exception as e:
                        result = json.dumps(
                            {"ok": False, "error": str(e)}, ensure_ascii=False
                        )

            result = self._compress_tool_content(result, max_chars=2000)

            if tool_name == "read_file" and "path" in args:
                visited_files.append(args["path"])

            event = {
                "event": "tool_executed",
                "tool_name": tool_name,
                "args": args,
                "result_preview": result[:400],
            }
            audit_records.append(event)
            self._append_jsonl(event)
            self._log(f"tool | {tool_name} | args={args}")

            try:
                parsed = json.loads(result)
            except Exception:
                parsed = None

            if tool_name == "read_file" and isinstance(parsed, dict):
                self._log(
                    f"read_file | path={args.get('path')} | ok={parsed.get('ok')}"
                )

            elif tool_name == "search_in_files" and isinstance(parsed, dict):
                matches = parsed.get("matches", [])
                files = sorted({m.get("file") for m in matches if m.get("file")})
                self._log(f"search_in_files | matched_files={files}")

            elif tool_name == "retrieve_documents" and isinstance(parsed, dict):
                results = parsed.get("results", [])
                files = sorted(
                    {r.get("source_path") for r in results if r.get("source_path")}
                )
                self._log(f"retrieve_documents | source_files={files}")

            tool_messages.append(ToolMessage(content=result, tool_call_id=tool_call_id))

        return {
            "messages": tool_messages,
            "tool_calls_count": state.get("tool_calls_count", 0)
            + len(last_msg.tool_calls),
            "visited_files": visited_files,
            "audit_log": audit_records,
            "last_tool_name": last_msg.tool_calls[0]["name"]
            if last_msg.tool_calls
            else "",
            "pending_tool_call": {},
            "last_tool_signature": current_signature if last_msg.tool_calls else "",
            "repeated_tool_calls": repeated_count,
        }

    def _format_final(self, state: AgentState) -> Dict[str, Any]:
        answer_text = self._extract_last_ai_message(state["messages"])

        prompt = (
            "Convert the following answer into a validated structured response.\n\n"
            f"Answer:\n{answer_text}\n\n"
            f"Visited files: {state.get('visited_files', [])}\n"
        )

        structured = self.final_model.invoke([HumanMessage(content=prompt)])
        final_response = structured.model_dump()

        event = {
            "event": "final_response",
            "final_response": final_response,
        }
        self._append_jsonl(event)

        # keep a normal AI message for the chat UI
        return {
            "messages": [AIMessage(content=final_response["answer"])],
            "final_response": final_response,
            "audit_log": [event],
        }

    def _stop_with_error(self, state: AgentState) -> Dict[str, Any]:
        started_at = state.get("started_at", time.time())
        elapsed = time.time() - started_at
        reason = "maximum number of tool calls reached"
        if elapsed > self.cfg.timeout_s:
            reason = "timeout reached"

        tool_feedback: List[ToolMessage] = []
        last_msg = state["messages"][-1] if state.get("messages") else None
        if isinstance(last_msg, AIMessage):
            tool_calls = getattr(last_msg, "tool_calls", []) or []
            for tc in tool_calls:
                tool_feedback.append(
                    ToolMessage(
                        content=json.dumps(
                            {"ok": False, "error": f"Stopped: {reason}"},
                            ensure_ascii=False,
                        ),
                        tool_call_id=tc["id"],
                    )
                )

        final_response = {
            "answer": f"Stopping because {reason}.",
            "sources": [],
        }
        event = {"event": "stopped", "reason": reason}
        self._append_jsonl(event)

        return {
            "messages": tool_feedback + [AIMessage(content=final_response["answer"])],
            "final_response": final_response,
            "audit_log": [event],
        }

    # ---------------------------------------------------------------
    # routers
    # ---------------------------------------------------------------

    def _route_after_model(self, state: AgentState) -> str:
        started_at = state.get("started_at", time.time())
        elapsed = time.time() - started_at
        if elapsed > self.cfg.timeout_s:
            return "stop"

        last_msg = state["messages"][-1]
        if not isinstance(last_msg, AIMessage):
            return "final"

        tool_calls = getattr(last_msg, "tool_calls", []) or []
        if not tool_calls:
            return "final"

        tool_calls_count = state.get("tool_calls_count", 0)
        max_tool_calls = state.get("max_tool_calls", self.cfg.max_tool_calls)

        if tool_calls_count + len(tool_calls) > max_tool_calls:
            return "stop"

        return "tools"

    def _route_after_human_review(self, state: AgentState) -> str:
        pending = state.get("pending_tool_call", {}) or {}
        decision = pending.get("decision", "approve")
        if decision == "approve":
            return "execute"
        if decision == "reject":
            return "execute"
        return "stop"
