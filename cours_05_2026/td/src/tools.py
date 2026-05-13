"""
Outils locaux pour un agent de lecture de fichiers.

NOTE logique des champs dans les outputs des tools.

- "ok"
  Permet de distinguer clairement succès et erreur.
  Avec ok: False, le LLM peut raisonner : l'outil a échoué,
  peut-être essayer autre chose ou demander a l'utilisateur.

- "truncated"
  Indique si le contenu a été tronqué (par exemple pour éviter
  de charger des fichiers trop gros).

- "max_bytes"
  Indique la limite de lecture utilisée.

- "max_matches"
  Indique la limite de matches utilisée (utile pour eviter qu'un dossier
  trop gros ne bloque l'agent).
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.safety import _is_text_file, safe_resolve_path

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------


@dataclass(frozen=True)
class ToolConfig:
    # Tous les chemins sont relatifs a base_dir. L'agent ne doit jamais pouvoir en sortir.
    base_dir: str
    # Limite de lecture pour éviter de charger des fichiers énormes dans le prompt.
    max_read_bytes: int = 50_000
    # Limite de lignes conservées par match pour éviter des sorties trop grandes.
    max_line_length: int = 300


def default_config() -> ToolConfig:
    # Par défaut on pointe vers le dossier courant au moment du lancement.
    return ToolConfig(base_dir=os.path.abspath("."))


# -------------------------------------------------------------------
# Tools que l'agent peut utiliser
# -------------------------------------------------------------------


def list_dir(path: str, cfg: ToolConfig) -> Dict[str, Any]:
    """
    Liste le contenu d'un dossier (non récursif).
    path est relatif a cfg.base_dir.
    """
    abs_path = safe_resolve_path(path, cfg)

    if not os.path.exists(abs_path):
        return {"ok": False, "error": "Path does not exist", "path": path}

    if not os.path.isdir(abs_path):
        return {"ok": False, "error": "Path is not a directory", "path": path}

    items: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(abs_path)):
        full = os.path.join(abs_path, name)
        try:
            st = os.stat(full)
            items.append(
                {
                    "name": name,
                    "type": "dir" if os.path.isdir(full) else "file",
                    "size_bytes": st.st_size if os.path.isfile(full) else None,
                }
            )
        except Exception as e:
            items.append({"name": name, "type": "unknown", "error": str(e)})

    return {"ok": True, "path": path, "items": items}


def read_file(
    path: str,
    cfg: ToolConfig,
    max_bytes: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Lit un fichier texte (utf-8). Coupe si trop gros.
    path est relatif a cfg.base_dir (notre sandbox).
    """
    abs_path = safe_resolve_path(path, cfg)

    if not os.path.exists(abs_path):
        return {"ok": False, "error": "File does not exist", "path": path}

    if os.path.isdir(abs_path):
        return {"ok": False, "error": "Path is a directory", "path": path}

    if not _is_text_file(abs_path):
        return {
            "ok": False,
            "error": "Refused: not a supported text file type",
            "path": path,
        }

    limit = int(max_bytes) if max_bytes is not None else cfg.max_read_bytes
    if limit <= 0:
        limit = cfg.max_read_bytes

    try:
        with open(abs_path, "rb") as f:
            data = f.read(limit + 1)
        truncated = len(data) > limit
        if truncated:
            data = data[:limit]

        text = data.decode("utf-8", errors="replace")
        return {
            "ok": True,
            "path": path,
            "truncated": truncated,
            "max_bytes": limit,
            "content": text,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "path": path}


def search_in_files(
    path: str,
    query: str,
    cfg: ToolConfig,
    max_matches: int = 50,
) -> Dict[str, Any]:
    """
    Recherche query (insensible a la casse) dans tous les fichiers texte
    sous path (récursif). Renvoie une liste de matchs {file, line, text}.
    """
    abs_root = safe_resolve_path(path, cfg)

    if not os.path.exists(abs_root):
        return {"ok": False, "error": "Path does not exist", "path": path}

    if not os.path.isdir(abs_root):
        return {"ok": False, "error": "Path is not a directory", "path": path}

    if query is None or str(query).strip() == "":
        return {"ok": False, "error": "query is required", "path": path}

    q = str(query).lower()
    max_matches = max(1, min(int(max_matches), 200))

    matches: List[Dict[str, Any]] = []
    base = os.path.abspath(cfg.base_dir)

    for root, _, files in os.walk(abs_root):
        for fn in files:
            abs_fp = os.path.join(root, fn)

            if not _is_text_file(abs_fp):
                continue

            rel_fp = os.path.relpath(abs_fp, base)

            try:
                with open(abs_fp, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, start=1):
                        if q in line.lower():
                            snippet = line.strip()
                            if len(snippet) > cfg.max_line_length:
                                snippet = snippet[: cfg.max_line_length] + "..."
                            matches.append({"file": rel_fp, "line": i, "text": snippet})
                            if len(matches) >= max_matches:
                                return {
                                    "ok": True,
                                    "path": path,
                                    "query": query,
                                    "matches": matches,
                                    "truncated": True,
                                    "max_matches": max_matches,
                                }
            except Exception:
                # On saute les fichiers illisibles pour ne pas bloquer l'agent.
                continue

    return {
        "ok": True,
        "path": path,
        "query": query,
        "matches": matches,
        "truncated": False,
        "max_matches": max_matches,
    }


# -------------------------------------------------------------------
# Registry (pratique pour agent.py)
# -------------------------------------------------------------------


def get_tools(cfg: ToolConfig):
    """
    Renvoie un dict {tool_name: callable} prêt a être utilisé par l'agent.
    """
    return {
        "list_dir": lambda **kwargs: list_dir(cfg=cfg, **kwargs),
        "read_file": lambda **kwargs: read_file(cfg=cfg, **kwargs),
        "search_in_files": lambda **kwargs: search_in_files(cfg=cfg, **kwargs),
    }
