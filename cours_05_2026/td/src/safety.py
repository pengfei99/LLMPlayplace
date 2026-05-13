import os

LIST_AUTHORIZED_FILE_EXTENSIONS = [
    ".txt",
    ".md",
    ".log",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".html",
    ".pdf",
]


def safe_resolve_path(rel_path: str, cfg) -> str:
    """
    Convertit un chemin relatif en chemin absolu, en interdisant de sortir
    de cfg.base_dir (notre sandbox). rel_path peut contenir des sous-dossiers
    (ex: "docs/rapport.txt").
    """
    if rel_path is None:
        raise ValueError("path is required")

    # Normalise et résout
    base = os.path.abspath(cfg.base_dir)
    target = os.path.abspath(os.path.join(base, rel_path))

    # Interdit de sortir de la sandbox
    if not (target == base or target.startswith(base + os.sep)):
        raise ValueError("Refused: path outside allowed base directory")

    return target


def _is_text_file(path: str) -> bool:
    # Heuristique simple. Pour ce TD, on évite de lire des fichiers binaires.
    _, ext = os.path.splitext(path.lower())
    return ext in set(LIST_AUTHORIZED_FILE_EXTENSIONS)
