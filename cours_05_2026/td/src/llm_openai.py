# llm_openai.py
# Backend OpenAI minimal pour remplacer llm_ollama.py
#
# Pré-requis:
#   pip install openai
#   export OPENAI_API_KEY="..."
#
# Cette version utilise la Responses API, recommandée pour les nouveaux projets.
# Pour cette première étape, on garde la même logique que précédemment:
# - on envoie une liste de messages
# - on récupère une sortie texte brute
# - agent.py continue à parser cette sortie comme avant

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from openai import OpenAI


@dataclass(frozen=True)
class OpenAIConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    timeout_s: int = 120
    max_output_tokens: int = 1200


def _messages_to_input(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert our simple {role, content} message format to the Responses API format.

    Important:
    - user/system/developer messages use content type "input_text"
    - assistant history messages use content type "output_text"
    """
    out: List[Dict[str, Any]] = []

    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")

        if not isinstance(content, str):
            content = str(content)

        if role in {"user", "system", "developer"}:
            out.append(
                {
                    "role": role,
                    "content": [
                        {
                            "type": "input_text",
                            "text": content,
                        }
                    ],
                }
            )
        elif role == "assistant":
            out.append(
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": content,
                        }
                    ],
                }
            )
        else:
            # Fallback: treat unknown roles as user input
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": content,
                        }
                    ],
                }
            )

    return out


def chat(
    messages: List[Dict[str, Any]],
    cfg: OpenAIConfig,
    *,
    stream: bool = False,
) -> str:
    """
    Appelle la Responses API et renvoie le texte produit par le modèle.

    Note:
    - Pour cette première étape, on reste sur une interface simple qui
      renvoie juste une string, afin de minimiser les changements dans agent.py.
    - Le streaming n'est pas implémenté ici pour garder le fichier simple.
    """
    if stream:
        raise NotImplementedError("Streaming not implemented in this minimal version.")

    client = OpenAI(timeout=cfg.timeout_s)

    response = client.responses.create(
        model=cfg.model,
        input=_messages_to_input(messages),
        temperature=cfg.temperature,
        max_output_tokens=cfg.max_output_tokens,
    )

    # Le SDK expose output_text pour récupérer le texte agrégé.
    text = getattr(response, "output_text", None)
    if isinstance(text, str):
        return text

    # Fallback défensif
    return str(response)


def healthcheck(cfg: OpenAIConfig) -> bool:
    """
    Vérifie grossièrement que l'appel API fonctionne.
    Attention: ce healthcheck consomme un mini appel API.
    """
    try:
        client = OpenAI(timeout=10)
        response = client.responses.create(
            model=cfg.model,
            input="Reply with exactly: ok",
            temperature=0.0,
        )
        text = getattr(response, "output_text", "")
        return isinstance(text, str) and "ok" in text.lower()
    except Exception:
        return False


def list_models() -> List[str]:
    """
    Liste les IDs de modèles visibles via l'API.
    Utile surtout pour debug.
    """
    client = OpenAI(timeout=20)
    models = client.models.list()

    out: List[str] = []
    for m in models.data:
        model_id = getattr(m, "id", None)
        if isinstance(model_id, str):
            out.append(model_id)

    return sorted(out)
