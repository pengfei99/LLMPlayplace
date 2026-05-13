"""
Interface terminal pour interagir avec l'agent.
On ajoute des fonctionnalites de RAG pour permettre a l'agent de
rechercher des informations dans des documents.
Il faut egalement gerer la memoire (memoire persistante et
memoire de travail)

Usage:
  python app_TD4_langgraph.py --model <model>
"""

import os
import sys

from openai import OpenAI

from src.agent_langgraph import AgentConfig
from src.agent_langgraph import FileAgentLangGraph as FileAgent
from src.llm_openai import OpenAIConfig
from src.llm_openai import healthcheck as healthcheck_openai
from src.llm_openai import list_models as list_models_openai
from src.memory import PersistentMemoryStore
from src.rag_store import RAGConfig, RAGStore
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

    #########################################################
    # --- Config LLM ---
    #########################################################

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

    #########################################################
    # --- Config Tools ---
    #########################################################

    tool_cfg = default_config()
    print(f"Sandbox BASE_DIR = {tool_cfg.base_dir}")

    #########################################################
    # --- Config RAG ---
    #########################################################

    client = OpenAI(timeout=llm_cfg.timeout_s)

    rag_store = RAGStore(
        data_dir="data",
        index_path=".rag_index.json",
        client=client,
        cfg=RAGConfig(
            embedding_model="text-embedding-3-small",
            chunk_size=800,
            chunk_overlap=120,
            top_k_default=4,
        ),
    )
    rag_store.build_or_load(rebuild=False)

    #########################################################
    # --- Config Memory ---
    #########################################################

    # On initialise la memoire persistante avec un fichier vide.
    memory_store = PersistentMemoryStore(
        memory_path=".memory.jsonl",
        client=client,
        embedding_model="text-embedding-3-small",
    )

    #########################################################
    # --- Config Agent ---
    #########################################################

    agent_cfg = AgentConfig(
        trace=False,
    )

    # Pour creer l'agent, il faut maintenant lui passer le store
    # de memoire persistante et le store de documents indexes.
    agent = FileAgent(
        tool_cfg=tool_cfg,
        llm_cfg=llm_cfg,
        rag_store=rag_store,
        memory_store=memory_store,
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
