"""
Interface terminal pour interagir avec l'agent.

Usage:
    python app_TD1_base.py --model <model>

Par exemple :
    python app_TD1_base.py --model qwen3.5:9b

Pré-requis:
  - Ollama tourne en local
  - Un modèle est disponible (ollama pull <model>)
  - Les autres fichiers sont dans le même dossier (ou PYTHONPATH correct)
"""

import argparse
import os
import sys

from src.agent import AgentConfig, FileAgent
from src.llm_ollama import (
    OllamaConfig,
)
from src.llm_ollama import (
    healthcheck as healthcheck_ollama,
)
from src.llm_ollama import (
    list_models as list_models_ollama,
)
from src.llm_openai import (
    OpenAIConfig,
)
from src.llm_openai import (
    healthcheck as healthcheck_openai,
)
from src.llm_openai import (
    list_models as list_models_openai,
)
from src.tools import default_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent local fichiers")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model to use")
    return parser.parse_args()


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


def main(model: str) -> None:
    print("=== Agent local fichiers ===")

    assert model in ["qwen3.5:9b", "gpt-4o-mini"], "Invalid model"

    #########################################################
    # --- Config LLM ---
    #########################################################

    # Si LLM en local via Ollama
    if model in ["qwen3.5:9b"]:
        llm_cfg = OllamaConfig(
            model=model,  # bien vérifier que le modèle est dans `ollama list`
            temperature=0.2,
            num_ctx=4096,
        )
        if (
            "OPENAI_API_KEY" not in os.environ
            or not os.environ["OPENAI_API_KEY"].strip()
        ):
            with open("openai_api_key.txt", "r") as f:
                api_key = f.read().strip()
            os.environ["OPENAI_API_KEY"] = api_key
        else:
            api_key = os.environ["OPENAI_API_KEY"]

        # Check that the model is responding
        if not healthcheck_ollama(llm_cfg):
            print("Err: Ollama is not responding on http://localhost:11434")
            print("Check that the service is running.")
            sys.exit(1)

        # Check that required model is available from Ollama
        try:
            available = list_models_ollama(llm_cfg)
        except Exception as e:
            print("Erreur: impossible de lister les modèles Ollama:", e)
            sys.exit(1)

        if llm_cfg.model not in available:
            print(f"Erreur: modèle Ollama introuvable: '{llm_cfg.model}'")
            if not available:
                print("Aucun modèle installé. Fais: ollama pull <modele>")
                sys.exit(1)

            print("Modèles disponibles:")
            for m in available:
                print("  -", m)

            sys.exit(1)

    # Si LLM en cloud via OpenAI
    elif model in ["gpt-4o-mini"]:
        llm_cfg = OpenAIConfig(
            model=model,
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
    else:
        raise ValueError(f"Invalid model: {model}")

    #########################################################
    # --- Config Tools ---
    #########################################################

    # Dans src.tools.py, on définit la configuration des outils qui permettent de lire et de rechercher dans les fichiers.
    # Ici on parle de 3 fonctions :
    # - list_dir : liste les fichiers et dossiers dans un dossier relatif a BASE_DIR
    # - read_file : lit un fichier texte relatif a BASE_DIR
    # - search_in_files : recherche dans les fichiers relatifs a BASE_DIR

    tool_cfg = default_config()
    print(f"Sandbox BASE_DIR = {tool_cfg.base_dir}")

    #########################################################
    # --- Config Agent ---
    #########################################################

    # Juste la configuration de l'agent, on peut changer les parametres si on veut
    agent_cfg = AgentConfig(
        max_steps=8,
        timeout_s=30,
        trace=False,
    )

    # La ou on a definit les differentes etapes de l'agent
    agent = FileAgent(
        tool_cfg=tool_cfg,
        llm_cfg=llm_cfg,
        agent_cfg=agent_cfg,
    )

    #########################################################
    # --- Boucle REPL ---
    #########################################################

    print("Type your question. /help for help.")

    while True:
        # On attend une question de l'utilisateur
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
                    if model in ["qwen3.5:9b"]:
                        models = list_models_ollama(llm_cfg)
                    elif model in ["gpt-4o-mini"]:
                        models = list_models_openai()
                    else:
                        raise ValueError(f"Invalid model: {model}")
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
    args = parse_args()
    main(args.model)
