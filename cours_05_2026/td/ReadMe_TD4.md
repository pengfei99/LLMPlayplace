# TD4 : Agents avec LangGraph

## Changements majeurs

Pour commencer, on ne modifie que le fichier [agent_langgraph.py](src/agent_langgraph.py). On garde la même logique que pour les agents précédents, mais on la rend explicite au lieu de laisser le LLM procéder dans sa boucle implicite. En pratique, dans le code, c’est la fonction `run` que l’on va considérablement simplifier. Comparez les deux fichiers [agent_openai_rag.py](src/agent_openai_rag.py) et [agent_langgraph.py](src/agent_langgraph.py).

Maintenant, `run` est très compacte :

```python
def run(self, user_input: str) -> str:
    initial_state: AgentState = {
        "messages": self.history + [HumanMessage(content=user_input)],
        "tool_calls_count": 0,
        "max_tool_calls": self.cfg.max_tool_calls
        }

    # Cela va exécuter les noeuds et les transitions définis ailleurs dans le graphe.
    final_state = self.graph.invoke(initial_state)

    # On garde l'historique complet pour le prochain tour
    self.history = final_state["messages"]

    # On récupère le dernier message "assistant" non tool-call
    final_text = self._extract_final_answer(final_state["messages"])
    return final_text
```

Toute l’heuristique explicite codée précédemment dans le `while True:` a disparu et est remplacée par `final_state = self.graph.invoke(initial_state)`. Magique ! Évidemment, c’est un peu de la triche : il faut quand même définir le graphe, les nœuds, les transitions, etc. Mais voyez comme le code devient maintenant plus structuré et plus facile à lire que la boucle `while` précédente.

On va donc définir explicitement les méthodes de classe :
* `_build_graph` : définit le graphe, c’est-à-dire les noeuds, les arêtes et les transitions. LangGraph prend ensuite le relais avec `graph.compile()`.
* `add_node` et `add_edge` : permettent de peupler le graphe avec ses différentes étapes et connexions.
* `_call_model` : correspond à l’appel explicite au LLM, c’est-à-dire au pipeline moteur d’inférence.
* `_route_after_model` : définit la politique de transition entre les nœuds, notamment en lisant les éventuels appels d’outils produits par le native tool calling.
* `_execute_tools` : reste la fonction la plus chargée : elle décrit concrètement comment exécuter un tool demandé par le modèle.
* `_too_many_tools` : ajoute un premier garde-fou pour éviter les boucles infinies, en imposant un nombre maximal d’appels d’outils.


bref, la boucle `while True:` devient :

```
START -> call_model
call_model -> execute_tools   si tool_call
call_model -> END             si réponse finale
call_model -> too_many_tools  si limite atteinte
execute_tools -> call_model
```

Et dans [app_langgraph_TD4.py](app_langgraph_TD4.py), tout ce qui change, ce sont les imports depuis `src.agent_langgraph` et la `AgentConfig` (lignes 83-86). Facile !


## Nota bene

Vous remarquerez que l’on a supprimé toute référence à la `WorkingMemory` dans ce nouveau code. C’est volontaire. La mémoire épisodique n’a pas complètement disparu : elle est simplement réduite, pour l’instant, à la liste `messages` présente dans l’état de l’agent. On verra ensuite comment la réintroduire plus proprement.
