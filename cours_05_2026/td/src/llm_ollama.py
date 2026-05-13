"""
Appel minimal a l'API locale Ollama.
Objectif: une fonction simple "chat" qui prend des messages et renvoie le texte du modèle.

Pré-requis:
- Ollama installé et en cours d'exécution (service local)
- Un modèle déjà "pull" via: ollama pull <model>

API docs: https://docs.ollama.com/reference/api
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List

import requests


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "mistral:latest"  # bien vérifier que le modèle est dans `ollama list`
    temperature: float = 0.2
    num_ctx: int = 4096
    timeout_s: int = 120  # timeout for HTTP requests
    max_output_tokens: int = 1200


def chat(
    messages: List[Dict[str, Any]],
    cfg: OllamaConfig,
    *,
    stream: bool = False,
) -> str:
    """
    Pour appeler l'endpoint /api/chat d'Ollama.
    messages: liste de dicts {role: "system"|"user"|"assistant", content: "..."}.
    Renvoie le texte renvoyé par le modèle.
    Ollama renvoie une structure JSON avec un champ message.content.
    """
    url = f"{cfg.base_url}/api/chat"

    payload: Dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": cfg.temperature,
            "num_ctx": cfg.num_ctx,
        },
    }

    if stream:
        # Streaming: on concatène les chunks.
        # Pour l’instant on renvoie la réponse complète, mais app.py pourra afficher au fil de l’eau.
        with requests.post(url, json=payload, stream=True, timeout=cfg.timeout_s) as r:
            r.raise_for_status()
            parts: List[str] = []
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                # Chaque chunk a typiquement: {"message":{"role":"assistant","content":"..."},"done":false,...}
                msg = obj.get("message") or {}
                chunk = msg.get("content")
                if chunk:
                    parts.append(chunk)

                if obj.get("done") is True:
                    break

            return "".join(parts)

    # Non streaming: réponse complète en une fois
    r = requests.post(url, json=payload, timeout=cfg.timeout_s)
    r.raise_for_status()
    obj = r.json()

    msg = obj.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"Unexpected Ollama response shape: {obj}")

    return content


def healthcheck(cfg: OllamaConfig) -> bool:
    """
    Vérifie qu'Ollama répond.
    """
    try:
        r = requests.get(f"{cfg.base_url}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def list_models(cfg: OllamaConfig) -> List[str]:
    """
    Liste les modèles disponibles localement via Ollama.
    """
    r = requests.get(f"{cfg.base_url}/api/tags", timeout=10)
    r.raise_for_status()
    obj = r.json()
    models = obj.get("models") or []
    out: List[str] = []
    for m in models:
        name = m.get("name")
        if isinstance(name, str):
            out.append(name)
    return out
