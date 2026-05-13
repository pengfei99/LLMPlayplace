# TD2 : Native Tool Calling avec l'API OpenAI

## Native tool calling

Dans [agent_openai_tools.py](src/agent_openai_tools.py), on utilise les fonctionnalités de tool calling natif de l'API OpenAI plutot que de définir les tools disponibles dans le prompt, et de forcer le modèle à retourner un output JSON structuré. Avant, on faisait tout à la main :
* description des tools
* instructions JSON
* envoi au modèle
* parsing du JSON de sortie
Le modèle devait imiter un protocole qu'on avait inventé : c'est bof !

Avec le tool calling natif, le prompt long et compliqué est remplacé par une méthode de classe `_tool_schemas()` dans `FileAgentOpenAITools`, qui liste les tools disponibles. Cela permet de supprimer :
* le prompt fragile
* le bricolage de JSON
* le parsing manuel
* les heuristiques de format

Le LLM derriere l'agent ne voit toujours qu'un prompt, mais la creation de ce prompt est geree en arriere-plan par OpenAI et est beaucoup plus robuste. L'API permet en effet de contraindre l’espace des sorties, la structure la réponse, et ainsi d'éviter les erreurs de format.

En pratique, l'API construit une representation structuree du contexte pour nous. Conceptuellement, c'est comme si on envoyait au LLM quelque chose comme :
```
SYSTEM
USER
ASSISTANT
TOOLS:
  list_dir(path)
  read_file(path)
  search_in_files(path, query)
```
Ca nous rappelle les inputs de l'API OpenAI vus pendant le cours LLM !
