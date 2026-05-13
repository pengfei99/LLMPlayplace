"""
Boucle agentique minimale:
- construire les messages (prompts.py)
- appeler le LLM via Ollama (llm_ollama.py)
- parser la sortie JSON (prompts.py)
- si tool_call: exécuter l'outil (tools.py), injecter le résultat, et boucler
- si final: renvoyer la réponse à l'utilisateur
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.llm_ollama import OllamaConfig
from src.llm_ollama import chat as chat_ollama
from src.llm_openai import OpenAIConfig
from src.llm_openai import chat as chat_openai
from src.prompts import build_messages_from_history, parse_model_json
from src.tools import ToolConfig, get_tools

# -------------------------------------------------------------------
# Config et état
# -------------------------------------------------------------------


@dataclass
class AgentConfig:
    max_steps: int = 8
    timeout_s: int = 180  # 3 minutes
    trace: bool = False  # affiche logs tool calls et erreurs
    max_json_retries: int = 1


@dataclass
class AgentState:
    """
    État minimal. Pour ce TD, on garde un simple historique de messages texte.
    """

    history: List[Dict[str, Any]] = field(default_factory=list)

    def reset(self) -> None:
        self.history.clear()


# -------------------------------------------------------------------
# Validation des tool calls
# -------------------------------------------------------------------


def _validate_tool_call(obj: Dict[str, Any], tool_names: List[str]) -> Tuple[bool, str]:
    if obj.get("type") != "tool_call":
        return False, "Not a tool_call"

    name = obj.get("name")
    if not isinstance(name, str) or name.strip() == "":
        return False, "Missing/invalid tool name"

    if name not in tool_names:
        return False, f"Unknown tool: {name}"

    args = obj.get("arguments")
    if args is None:
        return False, "Missing arguments"
    if not isinstance(args, dict):
        return False, "Arguments must be an object/dict"

    return True, ""


def _tool_result_message(tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role": "user",
        "content": (
            "Here is the result of the tool you requested.\n"
            f"tool={tool_name}\n"
            f"result={json.dumps(result, ensure_ascii=False)}\n\n"
            "Now decide the next step. "
            "If you need another tool, output a tool call. "
            "If you have enough information, output the final answer."
        ),
    }


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------


class FileAgent:
    def __init__(
        self,
        tool_cfg: ToolConfig,
        llm_cfg: Any,
        agent_cfg: Optional[AgentConfig] = None,
    ) -> None:
        self.tool_cfg = tool_cfg
        self.llm_cfg = llm_cfg
        self.cfg = agent_cfg or AgentConfig()
        self.state = AgentState()

        self.tools = get_tools(cfg=self.tool_cfg)
        self.tool_names = sorted(list(self.tools.keys()))

    def set_trace(self, enabled: bool) -> None:
        self.cfg.trace = enabled

    def reset(self) -> None:
        self.state.reset()

    def _log(self, msg: str) -> None:
        if self.cfg.trace:
            print(f"[trace] {msg}")

    def _chat(self, messages: List[Dict[str, Any]], stream: bool = False) -> str:
        if isinstance(self.llm_cfg, OllamaConfig):
            return chat_ollama(messages=messages, cfg=self.llm_cfg, stream=stream)
        elif isinstance(self.llm_cfg, OpenAIConfig):
            return chat_openai(messages=messages, cfg=self.llm_cfg, stream=stream)
        else:
            raise ValueError(f"Invalid LLM config: {self.llm_cfg}")

    def run(self, user_input: str) -> str:
        """
        Exécute une "réponse agent" complète, pouvant inclure plusieurs
        tool calls. Renvoie le texte final à afficher à l'utilisateur.
        """
        start = time.time()
        steps = 0
        json_retries = 0

        # On travaille sur une copie locale de l'historique (on commit a la fin)
        local_history = list(self.state.history)

        # Message utilisateur initial
        local_history.append({"role": "user", "content": user_input})

        while True:
            steps += 1
            # on verifie si on a atteint le nombre maximum d'etapes
            if steps > self.cfg.max_steps:
                self._log("max_steps reached")
                final = "Arrêt: nombre maximum d'étapes atteint. Reformuler la demande ou réduire le scope."
                # commit historique
                local_history.append({"role": "assistant", "content": final})
                self.state.history = local_history
                return final

            # on verifie si on a atteint le timeout
            if time.time() - start > self.cfg.timeout_s:
                self._log("timeout reached")
                final = "Arrêt: timeout. Essaie une demande plus simple ou un dossier plus petit."
                local_history.append({"role": "assistant", "content": final})
                self.state.history = local_history
                return final

            # Construit les messages envoyés au LLM.
            # Note: build_messages va re-injecter system + tools + history + user_input.
            # Ici, on lui passe tout l'historique local et le dernier input utilisateur
            # est déjà dans l'historique. Donc on passe user_input="" et on garde l'historique.
            # Pour rester simple, on passe le dernier user_input, et on retire le doublon:
            messages = build_messages_from_history(
                base_dir=self.tool_cfg.base_dir,
                history=local_history,
            )

            self._log(f"LLM call step {steps} (history={len(local_history)} messages)")

            # On envoie le prompt au LLM
            raw = self._chat(messages=messages, stream=False)

            # On parse la reponse du LLM pour verifier si on a un tool call ou un final
            obj = parse_model_json(raw)

            # Si JSON invalide, on tente une correction guidée 1 fois (configurable)
            if obj.get("type") == "error":
                self._log(f"RAW MODEL OUTPUT (first 500 chars): {raw[:500]!r}")
                self._log(f"Model JSON error: {obj.get('error')}")
                if json_retries < self.cfg.max_json_retries:
                    json_retries += 1
                    # On ajoute un rappel strict dans l'historique et on reboucle
                    local_history.append(
                        {
                            "role": "assistant",
                            "content": (
                                "Reminder: you MUST respond with ONLY valid JSON as specified. "
                                "No prose, no markdown. Output a single JSON object."
                            ),
                        }
                    )
                    continue

                final = (
                    "The model did not return a valid JSON. "
                    "Try another model, or reinforce the prompt."
                )
                local_history.append({"role": "assistant", "content": final})
                self.state.history = local_history
                return final

            # Final
            if obj.get("type") == "final":
                content = obj.get("content")
                if not isinstance(content, str):
                    content = "Erreur: champ 'content' manquant dans la réponse finale."
                local_history.append({"role": "assistant", "content": content})
                self.state.history = local_history
                return content

            # Tool call
            if obj.get("type") == "tool_call":
                # on verifie si le tool call est valide
                ok, err = _validate_tool_call(obj, self.tool_names)
                if not ok:
                    self._log(f"Invalid tool_call: {err}. Raw={obj}")
                    # On demande au modèle de corriger
                    local_history.append(
                        {
                            "role": "assistant",
                            "content": (
                                f"Tool call invalid: {err}. "
                                "Output a corrected tool_call JSON object."
                            ),
                        }
                    )
                    continue

                tool_name = obj["name"]
                arguments = obj["arguments"]

                self._log(f"Executing tool {tool_name} args={arguments}")

                # On exécute l'outil
                tool_fn = self.tools[tool_name]
                try:
                    result = tool_fn(**arguments)
                except Exception as e:
                    result = {"ok": False, "error": str(e)}

                # On injecte résultat outil
                local_history.append(_tool_result_message(tool_name, result))

                # Puis on boucle, le modèle va décider quoi faire avec le résultat
                continue

            # Type inattendu
            self._log(f"Unexpected model type: {obj.get('type')}")
            final = "Erreur: réponse inattendue du modèle."
            local_history.append({"role": "assistant", "content": final})
            self.state.history = local_history
            return final
