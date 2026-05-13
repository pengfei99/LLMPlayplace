"""
Interface terminal pour interagir avec l'agent.

Usage:
  python app_TD2_tool_calling.py --model <model>

Pré-requis:
  - Ollama tourne en local
  - Un modèle est disponible (ollama pull <model>)
  - Les autres fichiers sont dans le même dossier (ou PYTHONPATH correct)
"""

import os
import sys

from src.agent_openai_tools import AgentConfig
from src.agent_openai_tools import FileAgentOpenAITools as FileAgent
from src.llm_openai import OpenAIConfig
from src.llm_openai import healthcheck as healthcheck_openai
from src.llm_openai import list_models as list_models_openai
from src.tools import default_config


def print_help() -> None:
    print("""
Commandes disponibles:
  /help           Affiche cette aide
  /exit           Quitte le programme
  /reset          Réinitialise la mémoire de l'agent
  /trace on       Active les logs internes
  /trace off      Désactive les logs internes
  /models         Liste les modèles Ollama disponibles
""")


def main() -> None:
    print("=== Agent local fichiers ===")

    llm_cfg = OpenAIConfig(
        model="gpt-4o-mini",
        temperature=0.1,
        timeout_s=120,
        max_output_tokens=1200,
    )

    with open("openai_api_key.txt", "r") as f:
        api_key = f.read().strip()

    os.environ["OPENAI_API_KEY"] = api_key

    if not healthcheck_openai(llm_cfg):
        print(
            "Error: The OpenAI API is not responding, or the API key is absent/invalid."
        )
        print("Check OPENAI_API_KEY and the model name in the config.")
        sys.exit(1)

    # --- Config Tools ---
    tool_cfg = default_config()
    print(f"Sandbox BASE_DIR = {tool_cfg.base_dir}")

    # --- Config Agent ---
    agent_cfg = AgentConfig(
        max_steps=8,
        timeout_s=30,
        trace=False,
    )

    agent = FileAgent(
        tool_cfg=tool_cfg,
        llm_cfg=llm_cfg,
        agent_cfg=agent_cfg,
    )

    print("Type your question. /help for help.")

    while True:
        try:
            user_input = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        # --- Commandes spéciales ---
        # On peut définir ici des commandes spéciales pour l'agent,
        # comme le reset, le trace, etc. Cf. ce qui se fait dans Claude Code.
        if user_input.startswith("/"):
            cmd = user_input.lower()

            if cmd == "/exit":
                print("Goodbye.")
                break

            elif cmd == "/help":
                print_help()

            elif cmd == "/reset":
                agent.reset()
                print("Memory reset.")

            elif cmd == "/trace on":
                agent.set_trace(True)
                print("Trace on.")

            elif cmd == "/trace off":
                agent.set_trace(False)
                print("Trace off.")

            elif cmd == "/models":
                try:
                    models = list_models_openai()
                    print("Models available:")
                    for m in models:
                        print("  -", m)
                except Exception as e:
                    print("Error:", e)

            else:
                print("Unknown command. /help for list of commands.")

            continue

        # --- Exécution agent ---
        try:
            response = agent.run(user_input)
            print("\n" + response)
        except Exception as e:
            print("\nInternal error:", e)


if __name__ == "__main__":
    main()
