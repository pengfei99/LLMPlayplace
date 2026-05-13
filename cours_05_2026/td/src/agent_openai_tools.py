"""
Agent avec tool calling natif OpenAI.

Idée:
- On déclare les tools à l'API OpenAI (au lieu de les déclarer dans le prompt)
- Le modèle renvoie des tool_calls structurés
- On exécute les fonctions Python correspondantes
- On renvoie le résultat au modèle
- On boucle jusqu'à obtenir une réponse finale

Cette version remplace l'agent "JSON artisanal" par du tool calling natif.
Elle garde la même idée générale que l'agent précédent:
- état minimal
- historique de conversation
- max_steps
- timeout
- mode trace
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.llm_openai import OpenAIConfig
from src.tools import ToolConfig, get_tools

# -------------------------------------------------------------------
# Config et état de l'agent
# -------------------------------------------------------------------


@dataclass
class AgentConfig:
    max_steps: int = 8
    timeout_s: int = 30
    trace: bool = False


@dataclass
class AgentState:
    # Historique "chat" au format Chat Completions
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def reset(self) -> None:
        self.messages.clear()


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------


class FileAgentOpenAITools:
    def __init__(
        self,
        tool_cfg: ToolConfig,
        llm_cfg: OpenAIConfig,
        agent_cfg: Optional[AgentConfig] = None,
    ) -> None:
        self.tool_cfg = tool_cfg
        self.llm_cfg = llm_cfg
        self.cfg = agent_cfg or AgentConfig()
        self.state = AgentState()

        self.client = OpenAI(timeout=self.llm_cfg.timeout_s)
        self.tools = get_tools(cfg=self.tool_cfg)

    # ---------------------------------------------------------------
    # Utils
    # ---------------------------------------------------------------

    def set_trace(self, enabled: bool) -> None:
        self.cfg.trace = enabled

    def reset(self) -> None:
        self.state.reset()

    def _log(self, msg: str) -> None:
        if self.cfg.trace:
            print(f"[trace] {msg}")

    def _system_prompt(self) -> str:
        return f"""
You are a careful local file assistant.

You do NOT have direct filesystem access.
You can only inspect files and folders using the tools provided.

Rules:
- You may only work with paths relative to BASE_DIR.
- BASE_DIR = {self.tool_cfg.base_dir}
- Never invent file contents.
- If the answer requires evidence from files, use tools first.
- Prefer short targeted tool arguments.
- If a user asks about a client or a value, try to find the relevant file and read it before answering.
- Be concise and factual in final answers.
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
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative directory path, for example 'data'",
                            }
                        },
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
                            "path": {
                                "type": "string",
                                "description": "Relative file path, for example 'data/client_globex.txt'",
                            },
                            "max_bytes": {
                                "type": "integer",
                                "description": "Optional maximum number of bytes to read",
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
                    "description": "Search for a short query string inside all text files under a directory relative to BASE_DIR.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative directory path, for example 'data'",
                            },
                            "query": {
                                "type": "string",
                                "description": "Short search string, for example 'Globex' or 'Total 2025'",
                            },
                            "max_matches": {
                                "type": "integer",
                                "description": "Optional maximum number of matches",
                                "minimum": 1,
                                "maximum": 200,
                            },
                        },
                        "required": ["path", "query"],
                        "additionalProperties": False,
                    },
                },
            },
        ]

    def _base_messages(self) -> List[Dict[str, Any]]:
        return [{"role": "system", "content": self._system_prompt()}]

    def _build_messages(self, user_input: str) -> List[Dict[str, Any]]:
        # On garde l'historique accumulé + la nouvelle requête utilisateur
        return (
            self._base_messages()
            + self.state.messages
            + [{"role": "user", "content": user_input}]
        )

    def _create_completion(self, messages: List[Dict[str, Any]]):
        return self.client.chat.completions.create(
            model=self.llm_cfg.model,
            messages=messages,
            tools=self._tool_schemas(),
            tool_choice="auto",
            temperature=self.llm_cfg.temperature,
        )

    def _execute_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        if tool_name not in self.tools:
            return {"ok": False, "error": f"Unknown tool: {tool_name}"}

        tool_fn = self.tools[tool_name]
        try:
            result = tool_fn(**arguments)
            return (
                result if isinstance(result, dict) else {"ok": True, "result": result}
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------------------------------------------------------
    # API principale
    # ---------------------------------------------------------------

    def run(self, user_input: str) -> str:
        start = time.time()
        steps = 0

        messages = self._build_messages(user_input)

        while True:
            steps += 1

            if steps > self.cfg.max_steps:
                final = "Arrêt: nombre maximum d'étapes atteint."
                self.state.messages.extend(
                    [
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": final},
                    ]
                )
                return final

            if time.time() - start > self.cfg.timeout_s:
                final = "Arrêt: timeout."
                self.state.messages.extend(
                    [
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": final},
                    ]
                )
                return final

            self._log(
                f"LLM call step {steps} (history={len(self.state.messages)} messages)"
            )

            response = self._create_completion(messages)
            choice = response.choices[0]
            message = choice.message

            # -------------------------------------------------------
            # Cas 1. Le modèle demande un ou plusieurs tools
            # -------------------------------------------------------
            if message.tool_calls:
                assistant_message: Dict[str, Any] = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [],
                }

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    raw_args = tool_call.function.arguments

                    try:
                        arguments = json.loads(raw_args) if raw_args else {}
                        if not isinstance(arguments, dict):
                            arguments = {}
                    except Exception:
                        arguments = {}

                    self._log(f"Executing tool {tool_name} args={arguments}")

                    # On ajoute le tool_call assistant tel que renvoyé par l'API
                    assistant_message["tool_calls"].append(
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": raw_args or "{}",
                            },
                        }
                    )

                    result = self._execute_tool_call(tool_name, arguments)
                    self._log(
                        f"TOOL RESULT {tool_name}: {json.dumps(result, ensure_ascii=False)[:1000]}"
                    )

                    # Puis on renvoie le résultat comme message tool
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

                # Si plusieurs tool_calls, assistant_message n'a été ajouté qu'une fois
                if not any(m is assistant_message for m in messages):
                    # Sécurité défensive, normalement inutile
                    messages.append(assistant_message)

                continue

            # -------------------------------------------------------
            # Cas 2. Réponse finale
            # -------------------------------------------------------
            final_text = message.content or ""
            final_text = final_text.strip()

            self.state.messages.extend(
                [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": final_text},
                ]
            )

            return final_text
