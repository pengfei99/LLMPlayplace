On souhaite créer un site web très simple, organisé de la manière suivante :

website-agent-demo/
├── AGENT.md
├── site/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── outputs/

C'est tres simple et on pourrait le faire directement sur cursor, mais c'est illustratif de ce que l'on peut maintenant
facilement faire par exemple avec OpenClaw.

Avec AGENT.md qui a le contenu suivant :
```bash
# Website builder agent

Work only inside this workspace.

Goal:
Create a small static website in `site/`.

Required files:
- `site/index.html`
- `site/style.css`
- `site/app.js`

Task:
Build a landing page for a two-day course on AI agents.

Rules:
- No external dependencies.
- Clean modern design.
- Include hero section, course objectives, agenda, practical exercises, and call-to-action.
- After writing the files, explain how to run it locally with:

python -m http.server 8080 --directory site
```

L’objectif est simplement de demander à l’agent d’agir sur ces différents fichiers.

Dans cet exemple, l’agent n’utilise pas encore réellement d’outils externes ou de plugins complexes ; il s’agit d’un premier cas pédagogique simple permettant de comprendre la mécanique fondamentale d’un agent disposant d’un accès à un workspace local.

Cela permet d’illustrer plusieurs concepts essentiels :
- interaction avec un environnement de fichiers ;
- génération et modification de code ;
- structuration d’un projet ;
- exécution d’instructions complexes ;
- autonomie relative dans un cadre défini.

Autrement dit, avant d’exploiter pleinement des tools, plugins ou systèmes multi-agents plus avancés, on montre ici le socle minimal :
un modèle capable de raisonner, d’interagir avec des fichiers et de produire un artefact concret.



## Configuration de OpenClaw


Si l’on a déjà utilisé OpenClaw auparavant, on peut repartir de zéro en lancant la commande suivante dans le bon dossier:

```bash
openclaw reset
```

---

On commence par créer la structure du dossier :

```bash
mkdir -p website-agent-demo/site
cd website-agent-demo
```

---

On ajoute ensuite le contenu de `AGENT.md` :

```bash
vim AGENT.md
```

---

Si ce n’est pas déjà fait, on installe OpenClaw :

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

---

Sinon, on effectue l’onboarding :

```bash
openclaw onboard --install-daemon
```

Puis on choisit :

* Provider : OpenAI
* Modèle : `gpt-4o-mini`

---

## Verification du setting

On configure OpenClaw sur ce workspace :

```bash
openclaw config set agents.defaults.workspace "$(pwd)"
openclaw gateway restart
openclaw terminal
```

---

Dans le doute, on s’assure aussi que le PATH est correctement configuré :

```bash
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

On donne ensuite à l’agent le prompt suivant :

```bash
Read AGENT.md and create the website.
```

---

Pour observer le site web généré :

```bash
cd /home/thomas/Desktop/CODE/CEPE/cours_agents_td/openclaw_agents/website-agent-demo/site
python3 -m http.server 8000
```

---

Puis on ouvre le navigateur à l’adresse :

```txt id="5lq4nb"
http://localhost:8000/index.html
```


## Changer de modèle dans OpenClaw

### Méthode simple

Pour reconfigurer proprement un autre modèle ou provider :

```bash id="1nkz2w"
openclaw configure
```

---

Puis vérifier à nouveau :

```bash id="x6bm6o"
openclaw config get agents.defaults.model
```

---

Pour connaître l’état réel de l’agent :

```bash id="fepj1j"
openclaw agents list
```

### Méthode terminal

Si l’agent ne fonctionne pas correctement avec le modèle actuel, on peut basculer vers un modèle OpenAI :

```bash
openclaw config set agents.defaults.model "openai/gpt-4o-mini"
openclaw gateway restart
openclaw terminal
````

---

Il faut également renseigner la clé API OpenAI :

```bash id="2znqg8"
export OPENAI_API_KEY="sk-..."
```

---

Puis vérifier que le bon modèle est bien configuré :

```bash id="3t92bq"
openclaw config get agents.defaults.model
```

---







## Utiliser un modèle local avec OpenClaw

Pour utiliser un modèle local, il faut un moteur d’inférence capable d’exécuter le modèle et de l’exposer dans un format standardisé compatible avec OpenClaw.

### Installer Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
````

### Télécharger un modèle

Par exemple :

* `qwen2.5:7b` (généraliste)
* `qwen2.5-coder:7b` (spécialisé code)

```bash
ollama pull qwen2.5-coder:7b
```

### Lancer le modèle

```bash
ollama run qwen2.5-coder:7b
```

### Reconfigurer OpenClaw

```bash
openclaw configure
```

Puis choisir :

* Provider : Ollama
* Modèle : `qwen2.5-coder:7b`

### Vérifier la configuration

```bash
openclaw agents list
```

### Remarque

Les modèles locaux offrent :

* plus de confidentialité ;
* moins de dépendance aux APIs externes ;
* des coûts réduits.

Mais ils sont souvent :

* moins performants ;
* plus lents ;
* plus exigeants matériellement.
