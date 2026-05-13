import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.llm_openai import OpenAIConfig
from src.memory import PersistentMemoryStore, WorkingMemory
from src.rag_store import RAGStore
from src.tools import ToolConfig, get_tools


@dataclass
class AgentConfig:
    max_steps: int = 10
    timeout_s: int = 40
    trace: bool = False


class FileAgentOpenAIRAG:
    def __init__(
        self,
        tool_cfg: ToolConfig,
        llm_cfg: OpenAIConfig,
        rag_store: RAGStore,
        memory_store: PersistentMemoryStore,
        agent_cfg: Optional[AgentConfig] = None,
    ) -> None:
        self.tool_cfg = tool_cfg
        self.llm_cfg = llm_cfg
        self.rag_store = rag_store
        self.memory_store = memory_store
        self.cfg = agent_cfg or AgentConfig()

        self.client = OpenAI(timeout=self.llm_cfg.timeout_s)
        self.file_tools = get_tools(cfg=self.tool_cfg)
        self.working_memory = WorkingMemory()
        self.history: List[Dict[str, Any]] = []

    def set_trace(self, enabled: bool) -> None:
        self.cfg.trace = enabled

    def reset(self) -> None:
        self.history.clear()
        self.working_memory = WorkingMemory()

    def _log(self, msg: str) -> None:
        if self.cfg.trace:
            print(f"[trace] {msg}")

    def _system_prompt(self) -> str:
        wm = self.working_memory.summary_text()
        return f"""
        You are a careful document assistant with access to:
        1. file tools
        2. a retrieval tool over indexed documents
        3. a persistent memory store

        Memory policy:
        - Working memory is for the current session only.
        - Persistent memory is for durable, reusable facts across turns.
        - Before repeating a costly search, consider using search_memory.
        - Do not store trivial conversation history.
        - Store only compact facts that may help in future turns, such as:
        - where useful information was found
        - stable facts about the document collection
        - naming conventions or directory structure
        - reusable findings from previous exploration
        - Do not treat persistent memory as ground truth when the user asks for exact file contents. Use files or retrieval for verification.

        Tool strategy:
        - Use retrieve_documents when semantic retrieval is more efficient than raw file scanning.
        - Use read_file when you need exact text from a specific file.
        - Use search_memory when prior notes may save time or avoid repeated work.
        - Use remember_note only for durable, reusable facts.

        Current working memory:
        {wm if wm else "(empty)"}

        Be concise, factual, and grounded in retrieved evidence.
        """.strip()

    def _tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_dir",
                    "description": "List files and folders inside a directory relative to BASE_DIR.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a text file relative to BASE_DIR.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "max_bytes": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 200000,
                            },
                        },
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_in_files",
                    "description": "Search for a short string in text files under a directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "query": {"type": "string"},
                            "max_matches": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 200,
                            },
                        },
                        "required": ["path", "query"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "retrieve_documents",
                    "description": "Retrieve top relevant chunks from the indexed document store using semantic search.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_memory",
                    "description": "Search persistent memory for prior useful notes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remember_note",
                    "description": "Store a durable note in persistent memory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "kind": {"type": "string"},
                            "source": {"type": "string"},
                        },
                        "required": ["text"],
                        "additionalProperties": False,
                    },
                },
            },
        ]

    def _execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        if tool_name in self.file_tools:
            return self.file_tools[tool_name](**arguments)

        if tool_name == "retrieve_documents":
            result = self.rag_store.retrieve(
                query=arguments["query"],
                top_k=arguments.get("top_k", 4),
                rerank=False,
            )
            if result.get("ok"):
                self.working_memory.last_retrieved_chunks = result.get("results", [])
                paths = [
                    c.get("source_path")
                    for c in result.get("results", [])[:5]
                    if c.get("source_path")
                ]
                self.working_memory.set_recent_sources(paths)
            else:
                self.working_memory.add_failed_query(arguments["query"])

            return result

        if tool_name == "search_memory":
            result = self.memory_store.search(
                query=arguments["query"],
                top_k=arguments.get("top_k", 3),
            )
            if result.get("ok") and result.get("results"):
                top_texts = [r["text"] for r in result["results"][:2]]
                self.working_memory.add_note(
                    "Relevant memory found: " + " | ".join(top_texts)
                )
            else:
                self.working_memory.add_failed_query(f"memory:{arguments['query']}")
            return result

        if tool_name == "remember_note":
            return self.memory_store.append(
                text=arguments["text"],
                kind=arguments.get("kind", "episodic"),
                source=arguments.get("source", "agent"),
            )

        return {"ok": False, "error": f"Unknown tool: {tool_name}"}

    def _maybe_store_persistent_fact(self, user_input: str, final_text: str) -> None:
        """
        Very simple application-level memory policy.
        Store only compact reusable hints, not raw conversation turns.
        """
        if not final_text.strip():
            return

        if not self.working_memory.recent_sources:
            return

        note = (
            f"Topic: {user_input[:120]} | "
            f"Useful sources: {', '.join(self.working_memory.recent_sources[:3])}"
        )

        self.memory_store.append(
            text=note,
            kind="source_hint",
            source="agent",
            importance=2,
        )

    def run(self, user_input: str) -> str:
        self.working_memory.last_user_intent = user_input
        start = time.time()
        steps = 0

        messages = (
            [{"role": "system", "content": self._system_prompt()}]
            + self.history
            + [{"role": "user", "content": user_input}]
        )

        while True:
            steps += 1

            if steps > self.cfg.max_steps:
                return "Arrêt: nombre maximum d'étapes atteint."

            if time.time() - start > self.cfg.timeout_s:
                return "Arrêt: timeout."

            self._log(f"LLM call step {steps} (history={len(self.history)} messages)")

            response = self.client.chat.completions.create(
                model=self.llm_cfg.model,
                messages=messages,
                tools=self._tool_schemas(),
                tool_choice="auto",
                temperature=self.llm_cfg.temperature,
            )

            msg = response.choices[0].message

            if msg.tool_calls:
                assistant_message = {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [],
                }

                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    raw_args = tool_call.function.arguments or "{}"
                    try:
                        args = json.loads(raw_args)
                        if not isinstance(args, dict):
                            args = {}
                    except Exception:
                        args = {}

                    self._log(f"Executing tool {tool_name} args={args}")

                    assistant_message["tool_calls"].append(
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {"name": tool_name, "arguments": raw_args},
                        }
                    )

                    result = self._execute_tool(tool_name, args)
                    self._log(
                        f"TOOL RESULT {tool_name}: {json.dumps(result, ensure_ascii=False)[:800]}"
                    )

                    messages.append(assistant_message) if len(
                        assistant_message["tool_calls"]
                    ) == 1 else None
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

                if self.working_memory.last_retrieved_chunks:
                    sources = ", ".join(
                        sorted(
                            {
                                c["source_path"]
                                for c in self.working_memory.last_retrieved_chunks[:3]
                            }
                        )
                    )
                    self.working_memory.add_note(f"Recent retrieved sources: {sources}")

                continue

            final_text = (msg.content or "").strip()

            # Politique de mise à jour de la memoire persistante
            if final_text:
                if self.working_memory.recent_sources:
                    self.working_memory.add_note(
                        "Resolved using sources: "
                        + ", ".join(self.working_memory.recent_sources[:3])
                    )
                else:
                    self.working_memory.add_note(
                        "Resolved without new document retrieval."
                    )

                self._maybe_store_persistent_fact(user_input, final_text)

            self.history.extend(
                [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": final_text},
                ]
            )
            return final_text
