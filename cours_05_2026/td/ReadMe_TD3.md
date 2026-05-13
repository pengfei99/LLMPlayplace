# TD3 : Agent avec RAG et mémoire

Le but de ce TP est d’avoir un agent qui a accès à un dossier et qui peut faire appel à un outil RAG pour mieux atteindre ses objectifs.

Cela permet d’illustrer les deux points suivants :

- implémenter le concept de mémoire ;
- intégrer un RAG dans l’ensemble.


## Nouveaux scripts

On ajoute 2 fichiers : [memory.py](src/memory.py), [rag_store.py](src/rag_store.py), et on modifie le coeur de l'agent avec [agent_openai_rag.py](src/agent_openai_rag.py).

Dans [agent_openai_rag.py](src/agent_openai_rag.py), on ajoute 3 tools natifs (déclarés à l'API OpenAI en mode native tool calling):
* retrieve_documents : pour faire du RAG au lieu de scanner le fichier complet ;
* remember_note : pour stocker des informations importantes de manière durable dans la mémoire de l'agent ;
* search_memory : pour aller chercher dans la mémoire de l'agent (plutôt que dans les documents).

Pour la partie RAG, tout va être sauvegardé dans `.rag_index.json`, initialisé par `rag_store.build_or_load(rebuild=False)`.

## Gestion de la mémoire

L'agent dispose maintenant de deux types de mémoire : une mémoire de travail (`WorkingMemory`) et une mémoire persistante (`PersistentMemoryStore`). L’objectif est de distinguer ce qui est utile uniquement dans la session en cours, et ce qui doit être conservé pour être réutilisé plus tard.

Dans `WorkingMemory`, on structure explicitement l’état courant de l’agent. On ne se contente plus d’un simple historique textuel, mais on stocke différentes informations utiles au raisonnement :

* `session_notes` : notes récentes sur ce qui a été fait ;
* `last_retrieved_chunks` : derniers résultats de RAG ;
* `last_user_intent` : intention de l’utilisateur ;
* `recent_sources` : fichiers jugés utiles ;
* `recent_failed_queries` : requêtes inefficaces ;
* `open_question` : question en cours de résolution.

Le but est que l’agent ne reparte pas de zéro à chaque étape : il garde une trace de ce qu’il a déjà exploré, de ce qui a fonctionné ou non, et des sources pertinentes. Cette mémoire est injectée dans le prompt à chaque appel LLM.

La mémoire persistante (`PersistentMemoryStore`) sert à stocker des informations réutilisables entre tours et entre sessions. Contrairement à une simple journalisation, on ne stocke pas tout automatiquement. On introduit une politique d’écriture contrôlée côté code :

* on ne stocke pas les conversations brutes (Q/A) ;
* on stocke uniquement des faits compacts et utiles (par exemple : “tel type de document contient telle information”, ou “tel fichier est pertinent pour tel sujet”) ;
* on limite la taille des notes ;
* on évite les doublons via une déduplication simple (exacte et sémantique) ;
* on peut associer un niveau d’importance aux notes.

Cette politique est implémentée dans le code (et non uniquement dans le prompt), ce qui permet de contrôler précisément ce qui entre en mémoire. Cela illustre un principe important : le LLM propose, mais c’est le code de la pipeline agentique qui décide.

On ajoute également un usage explicite de la mémoire dans l’agent :

* `search_memory` permet de retrouver des informations déjà connues avant de relancer un retrieval coûteux ;
* les résultats pertinents sont injectés dans la mémoire de travail pour influencer les étapes suivantes ;
* en fin de réponse, l’agent peut décider de stocker un "résumé utile" (par exemple les sources pertinentes pour un sujet donné), plutôt que la réponse complète.

Enfin, la recherche dans la mémoire persistante ne repose pas uniquement sur la similarité d’embeddings : on pondère également les résultats par leur importance. Cela permet de privilégier les informations jugées plus utiles lors de leur stockage.

## Injection des retrieved chunks ##

Le RAG est géré en deux étapes dans le code [`agent_openai_rag.py`](src/agent_openai_rag.py) :

1. le LLM doit d’abord faire appel à `retrieve_documents`, au lieu de scanner le fichier entier ;
2. à partir des chunks obtenus, il peut ensuite produire sa réponse finale.

Le résultat de `retrieve_documents` est une liste de chunks, et non la réponse du LLM.

La réponse finale arrive dans un second temps : le LLM décide alors de ne pas faire appel à un tool et produit directement la réponse.

Supposons donc que le LLM décide de faire appel à l'outil `retrieve_documents`. Il va lancer `_execute_tool` avec `tool_name="retrieve_documents"`. Les chunks obtenus sont stockés dans
```bash
result = self.rag_store.retrieve(
    query=arguments["query"],
    top_k=arguments.get("top_k", 4),
    rerank=False,
)
```
Ils sont ensuite stockés dans l'historique des messages via
```bash
messages.append(
    {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps(result, ensure_ascii=False),
    }
)
```
et donc passés au LLM a l'itération suivante.

On les stocke également dans la working memory (pas essentiel ici)

## Parsing de documents ##

Maintenant qu'on rajoute du RAG, on va pouvoir donner des types de documents un peu plus complexes, comme des PDFs. On exclut encore les formats plus exotiques type .csv ou .xlsx parce qu'il y a un peu plus de travail a faire sur le parsing (pas difficile avec un assistant de code). Donc on en reste a des .txt, .md et .pdf (voir `LIST_AUTHORIZED_FILE_EXTENSIONS` dans [safety.py](src/safety.py) pour la liste des extensions autorisées.)

Dans le code on va utiliser `pymupdf4llm`, une version ameliorée de PyMuPDF (cf. les instructions d'installation dans [ReadMe_install.md](ReadMe_install.md)). Vous pouvez evidemment choisir votre package préferé en fonction des contenus des documents que vous voulez parser (texte seul, tableaux, images, etc.) et de vos contraintes (local avec RAM donnee, API ok, etc.).

## Ajout d'un registre de connaissances sur la structure des dossiers

Les fichiers stockés dans data le sont avec une certaine structure de dossiers connue de l'utilisateur. C'est un peu grossier que de demander à l'agent de s'y retrouver tout seul (au prix de recherches assez greedy dans l'architecture de fichiers) alors qu'on pourrait simplement lui passer des informations simples sur la structure des dossiers. 

A terme c'est typiquement une application possible de MCP (vous avez des données que vous voulez exposer) ou de gestion de la mémoire persistante via un fichier agent.md ou autre.