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
    base_dir: str
    max_read_bytes: int = 50_000
    max_line_length: int = 300

    # lecture
    allowed_read_roots: tuple[str, ...] = (
        "data/reports",
        "data/invoices",
        "data/clients",
    )
    blocked_read_roots: tuple[str, ...] = ("data/api", "data/hr", "data/secrets")

    # écriture
    allowed_write_roots: tuple[str, ...] = ("outputs",)
    blocked_write_roots: tuple[str, ...] = (
        "data",
        "data/api",
        "data/hr",
        "data/secrets",
    )


def default_config() -> ToolConfig:
    # Par défaut on pointe vers le dossier courant au moment du lancement.
    return ToolConfig(
        base_dir=os.path.abspath("."),
        allowed_read_roots=("data/reports", "data/invoices", "data/clients"),
        blocked_read_roots=("data/api", "data/hr", "data/secrets"),
        allowed_write_roots=("outputs",),
        blocked_write_roots=("data", "data/api", "data/hr", "data/secrets"),
    )


# -------------------------------------------------------------------
# Helpers de sécurité
# -------------------------------------------------------------------


def _is_under(abs_path: str, abs_root: str) -> bool:
    return abs_path == abs_root or abs_path.startswith(abs_root + os.sep)


def _check_read_permissions(abs_path: str, cfg: ToolConfig) -> None:
    blocked = [safe_resolve_path(p, cfg) for p in cfg.blocked_read_roots]
    allowed = [safe_resolve_path(p, cfg) for p in cfg.allowed_read_roots]

    if any(_is_under(abs_path, b) for b in blocked):
        raise ValueError("Refused: path is inside a blocked read area")

    if not any(_is_under(abs_path, a) for a in allowed):
        raise ValueError("Refused: path is outside allowed read areas")


def _check_write_permissions(abs_path: str, cfg: ToolConfig) -> None:
    blocked = [safe_resolve_path(p, cfg) for p in cfg.blocked_write_roots]
    allowed = [safe_resolve_path(p, cfg) for p in cfg.allowed_write_roots]

    if any(_is_under(abs_path, b) for b in blocked):
        raise ValueError("Refused: path is inside a blocked write area")

    if not any(_is_under(abs_path, a) for a in allowed):
        raise ValueError("Refused: path is outside allowed write areas")


# -------------------------------------------------------------------
# Tools que l'agent peut utiliser
# -------------------------------------------------------------------


def list_dir(path: str, cfg: ToolConfig) -> Dict[str, Any]:
    """
    Liste le contenu d'un dossier (non récursif).
    path est relatif a cfg.base_dir.
    """
    abs_path = safe_resolve_path(path, cfg)
    try:
        _check_read_permissions(abs_path, cfg)
    except Exception as e:
        return {"ok": False, "error": str(e), "path": path}

    if not os.path.exists(abs_path):
        return {"ok": False, "error": "Path does not exist", "path": path}

    if not os.path.isdir(abs_path):
        return {"ok": False, "error": "Path is not a directory", "path": path}

    sensitive_name_patterns = ["secret", "password", "salary", "token", "key"]

    items: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(abs_path)):
        full = os.path.join(abs_path, name)
        display_name = name
        if any(p in name.lower() for p in sensitive_name_patterns):
            display_name = "[redacted-sensitive-name]"

        try:
            st = os.stat(full)
            items.append(
                {
                    "name": display_name,
                    "type": "dir" if os.path.isdir(full) else "file",
                    "size_bytes": st.st_size if os.path.isfile(full) else None,
                }
            )
        except Exception as e:
            items.append({"name": display_name, "type": "unknown", "error": str(e)})

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
    try:
        _check_read_permissions(abs_path, cfg)
    except Exception as e:
        return {"ok": False, "error": str(e), "path": path}

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
    try:
        _check_read_permissions(abs_root, cfg)
    except Exception as e:
        return {"ok": False, "error": str(e), "path": path}

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


def write_text_file(
    path: str,
    content: str,
    cfg: ToolConfig,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Écrit un fichier texte dans le sandbox.
    Bonne pratique : limiter les écritures à un sous-dossier dédié.
    """
    abs_path = safe_resolve_path(path, cfg)
    try:
        _check_write_permissions(abs_path, cfg)
    except Exception as e:
        return {"ok": False, "error": str(e), "path": path}

    ext = os.path.splitext(abs_path.lower())[1]
    if ext not in {".txt", ".md", ".csv"}:
        return {
            "ok": False,
            "error": "Refused: unsupported file extension",
            "path": path,
        }
    if len(content) > 20000:
        return {"ok": False, "error": "Refused: content too large", "path": path}

    low = content.lower()
    suspicious_patterns = ["api_key", "password", "secret", "token", "-----begin"]
    if any(p in low for p in suspicious_patterns):
        return {
            "ok": False,
            "error": "Refused: content looks sensitive",
            "path": path,
        }

    # sécurité simple: n'autoriser l'écriture que dans outputs/
    allowed_root = safe_resolve_path("outputs", cfg)
    if not (abs_path == allowed_root or abs_path.startswith(allowed_root + os.sep)):
        return {
            "ok": False,
            "error": "Refused: writes are only allowed inside outputs/",
            "path": path,
        }

    parent = os.path.dirname(abs_path)
    os.makedirs(parent, exist_ok=True)

    if os.path.exists(abs_path) and not overwrite:
        return {
            "ok": False,
            "error": "File already exists. Use overwrite=true to replace it.",
            "path": path,
        }

    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "ok": True,
            "path": path,
            "bytes_written": len(content.encode("utf-8")),
            "overwrite": overwrite,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "path": path,
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
        "write_text_file": lambda **kwargs: write_text_file(cfg=cfg, **kwargs),
    }
