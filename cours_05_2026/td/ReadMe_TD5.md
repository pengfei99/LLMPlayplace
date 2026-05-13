# TD5 : Garde-fous, observabilité et human-in-the-loop

## Garde-fous et observabilité

NB : les garde-fous vont être définis dans le graphe et dans le code, pas dans le prompt.

On va commencer par ajouter plusieurs champs à l’état de l’agent, afin de garder une trace de ce qui se passe : les nœuds visités, les outils appelés et les fichiers consultés.
```python
class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    tool_calls_count: int
    max_tool_calls: int
    started_at: float
    audit_log: Annotated[List[Dict[str, Any]], operator.add]
    visited_files: Annotated[List[str], operator.add]
    last_tool_name: str
    pending_tool_call: Dict[str, Any]
    final_response: Dict[str, Any]
```

Les champs `audit_log` et `visited_files` vont être particulièrement utiles pour suivre ce que l’agent a fait.

Par rapport au code de l’agent précédent, on ajoute également un champ `max_tool_calls` à notre `AgentConfig`. Il permettra d’arrêter de force la progression dans le graphe si le nombre d’outils appelés devient trop important, afin d’éviter un coût excessif en tokens et, par exemple, de forcer l’utilisateur à reformuler sa requête.

### Observabilité

Dans le code, on ajoute trois niveaux d’observabilité :

* **Observabilité dans l’état de l’agent** : on garde une trace de ce qui se passe directement dans `AgentState`, par exemple avec les champs `audit_log`, `visited_files`, `last_tool_name` ou `final_response`.

* **Affichage en console pendant l’exécution** : certains événements importants peuvent être affichés pour comprendre ce que fait l’agent pas à pas, par exemple les nœuds visités, les outils appelés ou les fichiers consultés.

* **Sauvegarde des états de l’agent dans un log structuré** : on écrit les événements dans `.agent_trace.jsonl`, où chaque ligne correspond à un événement au format JSON.

Exemples :

```jsonl
{"event": "tool_executed", "tool_name": "read_file", "args": {...}}
{"event": "model_output", "tool_calls": [...]}
{"event": "final_response", "final_response": {...}}
```

Un fichier `.jsonl` est un fichier de logs où chaque ligne est un objet JSON indépendant.  
C’est pratique pour tracer l’exécution d’un agent, car on peut ajouter les événements un par un pendant que l’agent tourne.


### Validation de la réponse

On crée une classe `FinalAnswer` dans [schemas.py](src/schemas.py) pour définir la forme exacte que doit avoir la sortie de l’agent.

On ajoute ensuite une dernière étape de validation de l’output en le faisant passer par un second modèle. Ici, on utilise le même modèle OpenAI, mais en pratique on pourrait très bien utiliser un autre LLM, éventuellement plus petit ou spécialisé dans la validation.

```python
self.final_model = ChatOpenAI(...).with_structured_output(FinalAnswer)
```

Ce second modèle reçoit une instruction du type :

```text
Here is the answer: ...
Produce a JSON matching this schema:
{
  "answer": string,
  "sources": list[string]
}
```

L’output de ce modèle est ensuite validé automatiquement selon le schéma défini dans `FinalAnswer`.

C’est une étape essentielle pour des agents en production : elle permet de transformer une réponse libre du LLM en une sortie structurée, prévisible et plus facilement exploitable par le reste de l’application.

## Human-in-the-loop (HITL)

Le HITL se configure par une politique explicite appliquée à certains tools.

On ajoute un champ `interrupt_on_tools`, dans lequel on précise les outils pour lesquels une validation explicite de l’utilisateur est exigée. Cela peut être utile, par exemple, pour écrire une information dans la mémoire persistante, ou pour ouvrir et modifier un fichier sur la machine de l’utilisateur. L’exemple reste simple ici, mais le principe se généralise facilement à d’autres actions sensibles.

Lorsqu’un de ces tools est demandé par le modèle, l’agent interrompt son exécution et attend une décision humaine. L’utilisateur doit alors spécifier explicitement `"/approve"` pour que le tool soit effectivement exécuté, ou `"/reject"` pour refuser l’action.

C’est un comportement classique, que vous avez probablement déjà rencontré avec les assistants de code : l’agent peut proposer une action, mais certaines opérations nécessitent une validation humaine avant d’être réellement exécutées.

## Gestion de la mémoire et du prompt

Par rapport aux TDs précédents, on ajoute également un peu de code pour gérer la longueur des prompts et de l’historique.

Jusqu’ici, on ne s’en était pas trop préoccupé, mais avec du RAG, même basique, on peut rapidement dépasser la taille de la fenêtre de contexte. En effet, l’agent accumule à la fois l’historique de conversation, les messages intermédiaires, les résultats d’outils et les documents récupérés.

Il devient donc nécessaire de contrôler ce que l’on garde dans le contexte envoyé au modèle : par exemple tronquer l’historique, limiter le nombre de documents injectés, résumer certains échanges, ou conserver uniquement les informations les plus utiles.

Cette fois-ci, on va s'assurer que dans l'historique des messages (stocke dans `self.history`), on ne garde que :
* les `HumanMessage` (inputs utilisateurs)
* les `AIMessage` finaux (les resultats finaux)
et on va jeter ou compresser :
* les `ToolMessage` (ils restent sauves dans le .log, pas de panique)
* les gros résultats RAG (pas besoin de garder les chunks de texte).

On a également amélioré le prompt, car la version précédente faisait que le LLM se comportait encore trop comme un assistant généraliste, et pas suffisamment comme un agent local dont le premier réflexe doit être d’inspecter les fichiers. En particulier, il faut insister dans le prompt sur le fait que :

- le LLM a accès aux documents locaux via les tools ;
- il doit utiliser ces tools avant de répondre qu’il ne sait pas ou qu’il ne connaît pas la réponse ;
- si la question porte sur des rapports, factures, documents internes ou fichiers présents sur la machine, la stratégie par défaut est de chercher dans les fichiers avant de répondre.

L’objectif est de modifier le comportement par défaut de l’agent : il ne doit pas seulement raisonner à partir de ses connaissances générales, mais exploiter activement les outils locaux dont il dispose.

## Checkpointing

LangGraph fournit nativement des mécanismes d’interruption pour le human-in-the-loop, mais ceux-ci nécessitent un checkpointer et un `thread_id` afin de pouvoir reprendre l’exécution au bon endroit. Le checkpointing permet de sauvegarder l’état du graphe à différents moments de son exécution. Ainsi, lorsqu’un agent s’interrompt pour demander une validation humaine, on peut reprendre exactement depuis l’état sauvegardé, sans relancer toute l’exécution depuis le début.

Cette persistance sert aussi de base au **time travel** qui permet de revenir à un état précédent du graphe, d’inspecter ce qui s’est passé, ou de rejouer une exécution à partir d’un checkpoint donné. C’est utile pour déboguer, comprendre pourquoi l’agent a pris une décision, ou tester une autre suite d’actions sans tout relancer depuis le début.

Pour ajouter un checkpointer, c’est très simple : on l’instancie, puis on le passe au moment de compiler le graphe.
```python
from langgraph.checkpoint.memory import InMemorySaver

self.checkpointer = InMemorySaver()
graph.compile(checkpointer=self.checkpointer)
```

LangGraph fait le travail pour nous : le checkpointer sauvegarde automatiquement les checkpoints pendant l’exécution du graphe. Il faut ensuite décider lesquels on souhaite exposer à l’utilisateur pour faire du *time travel*. Typiquement, on ne veut pas afficher tous les checkpoints intermédiaires, mais seulement ceux qui correspondent à la fin d’un tour complet de l’agent.

Pour cela, on sélectionne les checkpoints pour lesquels il n’y a plus de prochain noeud à exécuter, c’est-à-dire ceux où `next == ()` :

```python
is_final = tuple(snap.next) == ()
```

On ajoute plusieurs méthodes de classe à `FileAgentLangGraphAdvanced` :

- `list_checkpoints` : liste les checkpoints disponibles ;
- `replay_from_checkpoint` : relance l’agent à partir d’un checkpoint donné ;
- `get_checkpoint_state` : inspecte un résumé de l’état de l’agent à un checkpoint donné.

Ces méthodes permettent d’exposer une partie du checkpointing à l’utilisateur, notamment pour comprendre ce qui s’est passé pendant l’exécution ou rejouer l’agent depuis un état antérieur. Il suffit ensuite de faire
```bash
\checkpoints  # lister les checkpoints disponibles
\checkpoint <ckpt-id>  # inspecter un checkpoint donne
\replay <ckpt-id>  # relancer a partir du checkpoint
```

Attention : dans cette version simple, le *time travel* ne va pas annuler les éventuelles modifications de l’environnement effectuées entre-temps.
Par exemple, si l’agent a écrit ou modifié un fichier texte, revenir à un checkpoint précédent ne restaurera pas automatiquement l’ancien état du fichier. Le checkpoint sauvegarde l’état du graphe, pas nécessairement l’état complet du monde extérieur.
Pour obtenir ce comportement, il faudrait un mécanisme plus avancé, par exemple sauvegarder une image complète de l’environnement, ou gérer les fichiers avec une logique de versionnement de type Git.


## Pratiquement

### Illustrer l’observabilité simple

Pour voir les traces on peut faire la chose suivante
```bash
/trace on
```
Pour ensuite regarder le .jsonl des traces on peut faire
```bash
head -n 5 .agent_trace.jsonl
tail -n 20 .agent_trace.jsonl
```
Chaque ligne de `.agent_trace.jsonl` correspond à un événement de l’exécution de l’agent : appel de modèle, appel de tool, réponse finale, etc.

### Observer le Human In The Loop

Dans notre config, on a :

```python
interrupt_on_tools={"write_text_file"}
```

Donc le HITL se déclenche quand le modèle veut utiliser le tool `write_text_file`. Il faut donc lui demander une action d’écriture. Par exemple :

```text
Crée un fichier notes_demo.txt dans le dossier autorisé avec le texte suivant : "Ceci est une démonstration du human-in-the-loop."
```
Si on tape une autre question normale, on devrait voir :
```text
A tool call is pending. Use /approve or /reject.
```

### Illustrer les checkpoints

Après avoir fait quelques tours de conversation, on peut ecrire dans l'interface de chat

```text
> /checkpoints
> /checkpoint <id>
> /replay <id>
```