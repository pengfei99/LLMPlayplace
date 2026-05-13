# TD1 : coder un Agent de zero avec Ollama (en local) et OpenAI (API).

Ici, on veut simplement créer un agent qui a accès à une structure de fichiers afin d’illustrer :

- comment faire une boucle avec plusieurs appels LLM ;
- comment tester avec un LLM local ou via une API dans la boucle agentique ;
- comment gérer naïvement l’appel à des fonctions Python dans la boucle agentique.

En particulier, dans le fichier `src/tools.py`, on définit un ensemble de fonctions permettant d’effectuer des actions sur des structures de fichiers.

On va donc illustrer la boucle agentique minimale : 
- construire les messages
- appeler le LLM
- parser la sortie JSON pour appeler une fonction quand necessaire
- si tool_call: exécuter l'outil (tools.py), injecter le résultat, et boucler
- si final: renvoyer la réponse à l'utilisateur

C'est ce que cursor permet de faire, mais avec ce code, nous avons un controle complet sur toute la chaine.

## How to run

```
python app_TD1_base.py --model <model>
```
avec `model` soit un modele de OpenAI, soit un modele disponible via Ollama.

## Structure de l'agent local

Suivons le cheminement exact d'une requête à notre agent.

Dans [app.py](app.py), on a codé notre boucle REPL (Read Eval Print Loop).

La requête initiale est envoyée à l'agent via `response = agent.run(user_input)`. On entre alors dans `FileAgent.run(...)`.

On commence par ajouter la question (`user_input`) a l'historique actuel de messages `local_history` (on travaille sur une copie qu'on pushe dans l'état de l'agent à la fin) :

```
local_history = list(self.state.history)
local_history.append({"role": "user", "content": user_input})
```

Ensuite, on va boucler via `while True`. A chaque étape, le prompt pour le LLM est construit via 

```
messages = build_messages_from_history(
    base_dir=self.tool_cfg.base_dir,
    history=local_history,
)
```

ce qui ajoute au prompt :
- le system_prompt de base
- la description des tools
- l’historique
- la question utilisateur

On envoie ca ensuite au LLM via

```
raw = chat(messages=messages, cfg=self.llm_cfg, stream=False)
```

Puis on interprete l(= parsing) le JSON-structured output avec

```
obj = parse_model_json(raw)
```

On se rappelle que le modele doit renvoyer un JSON du type

```
{
  "type": "tool_call",
  "name": "search_in_files",
  "arguments": {
    "path": "comptes_rendus",
    "query": "client"
  }
}
```

avec `type` qui peut etre soit `"tool_call"` (le LLM a décidé d'appeler un outil, on continue dans la boucle) soit `"final"` (il a trouvé la réponse finale, et on sort de la boucle).

* Si `type == "final"`, on termine la boucle en renvoyant le dernier contenu du JSON-structured output (qui est la réponse finale).

* Si `type == "tool_call"`, on commence par valider le tool call que le LLM a decidé :

  ```
  ok, err = _validate_tool_call(obj, self.tool_names)
  ```

  On exécute ensuite le tool :

  ```
  tool_fn = self.tools[tool_name]
  result = tool_fn(**arguments)
  ```

  On met à jour l'historique des actions (tool call et tool result) :

  ```
  local_history.append(_tool_call_message(tool_name, arguments))
  local_history.append(_tool_result_message(tool_name, result))
  ```

  Puis ca repart, avec cette fois-ci le prompt au LLM qui contient l'input de départ, ainsi que le premier tool call et son résultat.
