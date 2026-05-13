"""
prompts.py

Objectif du script : forcer le LLM à produire soit :
- une réponse finale en texte,
- ou un JSON strict décrivant un appel d'outil

Pour éviter le parsing fragile, on impose un wrapper très clair.
Si le modèle veut appeler un outil, il doit répondre uniquement
par un JSON avec les clés 'type', 'name', 'arguments'.

Si le modèle veut répondre à l'utilisateur, il doit répondre
uniquement par un JSON avec 'type'="final" et 'content'.

Ensuite l'agent n'a plus qu'à faire json.loads(...).
"""

import json
from typing import Any, Dict, List


def system_prompt(base_dir: str) -> str:
    """
    MAIN PROMPT pour l'agent (instructions globales).

    On insiste sur:
    - usage des tools uniquement via JSON
    - pas d'accès hors du `base_dir`
    - concision dans les messages/réponses
    """
    return f"""
    You are a local file assistant running on the user's machine.

    SANDBOX
    - You may only access files under BASE_DIR.
    - BASE_DIR = {base_dir}
    - All paths must be relative to BASE_DIR.
    - Never use absolute paths.
    - Never use '..' or attempt to escape BASE_DIR.

    AVAILABLE TOOLS
    You do NOT have direct filesystem access.
    You can only inspect files and folders by calling tools.

    You have these tools:
    - list_dir(path)
    - read_file(path, max_bytes?)
    - search_in_files(path, query, max_matches?)

    CRITICAL OUTPUT RULES
    1) Your entire response must be exactly one of:
    - a tool call
    - a final answer
    2) Output only one action at a time.
    3) Do not add explanations before or after the action.
    4) Prefer concise outputs.
    5) Valid output formats are:

    Tool call:
    {{
    "type": "tool_call",
    "name": "list_dir" | "read_file" | "search_in_files",
    "arguments": {{ ... }}
    }}

    Final answer:
    {{
    "type": "final",
    "content": "..."
    }}

    TOOL USAGE STRATEGY
    You must behave like a careful file investigator.

    When the user asks a question about data in files:
    - Do NOT ask for clarification if a reasonable search strategy exists.
    - Start by exploring available files if needed.
    - Use short, targeted search queries.
    - Prefer searching for entity names, filenames, or short keywords.
    - Do NOT use the full natural-language user question as a search query.

    Examples of good search queries:
    - "Globex"
    - "ACME"
    - "Total 2025"
    - "2025-03"

    Examples of bad search queries:
    - "What is the 2025 total for Globex?"
    - "Can you find the total annual sales for this client?"

    DEFAULT BEHAVIOR
    - If the user asks about a client or a value and the location is not fully explicit, first inspect the likely directory structure.
    - If a directory like "data" exists, use it instead of asking the user.
    - If the user asks for a value about one client, try to locate the relevant file, then read it.
    - Do not answer from guesswork.
    - Do not stop after a search if reading a file is still necessary.

    EXPECTED REASONING PATTERNS
    1) Need to know what files exist:
    -> call list_dir
    2) Need to find which file mentions an entity:
    -> call search_in_files with a short query such as a client name
    3) Need the exact value:
    -> call read_file on the relevant file
    4) Only after reading enough evidence:
    -> return a final answer

    WHEN TO ASK THE USER
    Ask the user a clarification question only if:
    - the relevant directory or file truly cannot be inferred
    - multiple interpretations remain after using the tools
    - the tool results are insufficient

    IMPORTANT
    - Never fabricate file contents.
    - Never claim you read a file if you did not call a tool.
    - Prefer multiple tool calls over an unsupported guess.
    - If you already have enough evidence in the tool results, answer directly.

    Remember: output exactly one JSON object and nothing else.
    """.strip()


def system_prompt_ollama(base_dir: str) -> str:
    """
    MAIN PROMPT pour l'agent (instructions globales).

    On insiste sur:
    - usage des tools uniquement via JSON
    - pas d'accès hors du `base_dir`
    - concision dans les messages/réponses
    """
    return f"""
    You are a local file assistant running on the user's machine.

    SANDBOX
    - You may only access files under BASE_DIR.
    - BASE_DIR = {base_dir}
    - All paths you mention MUST be relative to BASE_DIR.
    - Never attempt absolute paths. Never attempt '..'. Never attempt to escape BASE_DIR.

    TOOLS
    You can use tools to inspect and read files. You do NOT have direct access to the filesystem.
    If you need file content or directory listings, you MUST call a tool.

    CRITICAL OUTPUT RULES (NO EXCEPTIONS)
    1) Your entire response MUST be a single valid JSON object.
    2) Output ONLY JSON. No extra text, no explanations, no markdown, no code fences.
    3) Do NOT output labels like TOOL_CALL, TOOL_RESULT, FINAL, or key=value lines.
    4) Do NOT wrap the JSON in ``` or any other formatting.
    5) Always use double quotes for JSON keys and string values.

    DECISION
    - If you need to call a tool, output a JSON object of type "tool_call".
    - If you can answer the user now, output a JSON object of type "final".

    JSON SCHEMAS (FOLLOW EXACTLY)

    Tool call:
    {{
    "type": "tool_call",
    "name": "list_dir" | "read_file" | "search_in_files",
    "arguments": {{ ... }}
    }}

    Final answer:
    {{
    "type": "final",
    "content": "..."
    }}

    TOOL ARGUMENTS
    - list_dir: arguments MUST be {{ "path": "<relative_dir>" }}
    - read_file: arguments MUST be {{ "path": "<relative_file>", "max_bytes": <optional_int> }}
    - search_in_files: arguments MUST be {{ "path": "<relative_dir>", "query": "<string>", "max_matches": <optional_int> }}

    ERROR HANDLING
    - If a tool result contains ok=false or an error field, decide whether to try a different tool or ask the user for clarification.
    - If the user request is ambiguous, ask a precise question using type="final".

    REMEMBER
    Your response MUST be a SINGLE JSON OBJECT and nothing else.
    """.strip()


def tools_description() -> str:
    """
    Description textuelle des outils, injectée dans le prompt.
    """
    return """
    Available tools:
    - list_dir(path: string)
    Lists files and folders inside the directory at 'path' (relative to BASE_DIR).

    - read_file(path: string, max_bytes?: int)
    Reads a text file at 'path' (relative to BASE_DIR). May return truncated content.

    - search_in_files(path: string, query: string, max_matches?: int)
    Searches for 'query' in all text files under 'path' (relative to BASE_DIR).
    """.strip()


def build_messages_from_history(base_dir: str, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = []
    messages.append({"role": "system", "content": system_prompt(base_dir)})
    messages.append({"role": "system", "content": tools_description()})
    messages.extend(history)
    return messages


def parse_model_json(text: str) -> Dict[str, Any]:
    """
    Parse la sortie du modèle.

    Formats acceptés :
    1) JSON strict :
       {"type": "tool_call", "name": "...", "arguments": {...}}
       {"type": "final", "content": "..."}

    2) Format texte tool call :
       TOOL_CALL
       tool=list_dir
       arguments={"path": "data"}

    3) Format texte final :
       FINAL
       content=Some answer here

    4) Fallback :
       - si texte libre non vide, on le traite comme une réponse finale
       - si vide, erreur
    """
    if text is None:
        return {"type": "error", "error": "Model returned None", "raw": ""}

    text = text.strip()

    if text == "":
        return {"type": "error", "error": "Model returned empty output", "raw": ""}

    # ------------------------------------------------------------
    # 1) Retire d'éventuelles code fences Markdown
    # ------------------------------------------------------------
    if text.startswith("```"):
        lines = text.splitlines()

        # retire première ligne ``` ou ```json
        if lines:
            lines = lines[1:]

        # retire dernière ligne ``` si présente
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # ------------------------------------------------------------
    # 2) Essaie d'abord le JSON strict
    # ------------------------------------------------------------
    try:
        obj = json.loads(text)
        if not isinstance(obj, dict):
            return {
                "type": "error",
                "error": "Model JSON is not an object",
                "raw": text[:2000],
            }
        if "type" not in obj:
            return {
                "type": "error",
                "error": "Missing 'type' in model JSON",
                "raw": text[:2000],
            }
        return obj
    except Exception:
        pass

    # ------------------------------------------------------------
    # 3) Support du format:
    #    TOOL_CALL
    #    tool=search_in_files
    #    arguments={"path": ".", "query": "Globex"}
    # ------------------------------------------------------------
    if text.startswith("TOOL_CALL"):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        tool_name = None
        arguments = None

        for line in lines[1:]:
            if line.startswith("tool="):
                tool_name = line.split("=", 1)[1].strip()
            elif line.startswith("arguments="):
                args_str = line.split("=", 1)[1].strip()
                try:
                    parsed_args = json.loads(args_str)
                    if isinstance(parsed_args, dict):
                        arguments = parsed_args
                except Exception:
                    return {
                        "type": "error",
                        "error": "Invalid JSON in TOOL_CALL arguments",
                        "raw": text[:2000],
                    }

        if tool_name and arguments is not None:
            return {
                "type": "tool_call",
                "name": tool_name,
                "arguments": arguments,
            }

        return {
            "type": "error",
            "error": "Invalid TOOL_CALL format",
            "raw": text[:2000],
        }

    # ------------------------------------------------------------
    # 4) Support du format:
    #    FINAL
    #    content=...
    # ------------------------------------------------------------
    if text.startswith("FINAL"):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        content_parts = []

        for line in lines[1:]:
            if line.startswith("content="):
                content_parts.append(line.split("=", 1)[1])
            else:
                content_parts.append(line)

        content = "\n".join(content_parts).strip()
        return {
            "type": "final",
            "content": content,
        }

    # ------------------------------------------------------------
    # 5) Fallback utile pour les modèles peu disciplinés :
    #    texte libre non vide => réponse finale
    # ------------------------------------------------------------
    return {
        "type": "final",
        "content": text,
    }

# def parse_model_json(text: str) -> Dict[str, Any]:
#     """
#     Strict parsing: on attend du JSON pur.
#     Si le modèle sort du texte, on échoue proprement ('type'='error').
#     """
#     text = text.strip()

#     # Certains modèles entourent le JSON avec ```json ...```
#     if text.startswith("```"):
#         # On retire les fences si présentes
#         text = text.strip("`")
#         # Et on enlève un éventuel 'json' de première ligne
#         text = text.replace("\njson\n", "\n", 1)

#     try:
#         obj = json.loads(text)
#     except Exception as e:
#         return {
#             "type": "error",
#             "error": f"Model did not return valid JSON: {e}",
#             "raw": text[:2000],
#         }

#     if not isinstance(obj, dict):
#         return {
#             "type": "error",
#             "error": "Model JSON is not an object",
#             "raw": text[:2000],
#         }

#     if "type" not in obj:
#         return {
#             "type": "error",
#             "error": "Missing 'type' in model JSON",
#             "raw": text[:2000],
#         }

#     return obj
