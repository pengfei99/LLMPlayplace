La documentation dans OpenClaw est plutot bien faite, voir https://docs.openclaw.ai/start/getting-started

##
# Structure du dossier
##

Voici la structure du projet d'agent dont l'objectif est d'etre capable d'extraire les dates de rapports financiers et de les exporter
en .ics  afin de pouvoir directement les integrer dans un calendrier.

openclaw-mining-demo/
├── input_docs/
├── outputs/
└── skills/
    └── mining-deadlines/
        ├── SKILL.md
        └── bin/
            ├── build_ics.py
            └── validate_deadlines.py


my-skill/
  SKILL.md
  scripts/
    ├── build_ics.py
    └── validate_deadlines.py
  references/
  assets/

Explication sommaire :
----------------------

Le dossier bin/ contient les outils exécutables. Le fichier SKILL.md est la “notice d’utilisation” de ces outils.
bin/ = les outils, c.a.d. des scripts que l'on va demander a l'agent d'utiliser.
SKILL.md = la notice (ici on ne l'utilise pas vraiment, on a juste garder pour la structure)
prompt = Dans le prompt on definira l’objectif.
OpenClaw = le runtime qui lit l’objectif, consulte la skill, puis utilise les scripts quand c’est pertinent.

##
#
## 

Pour installer openclaw sur ordinateur
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```
On crée la structure du dossier
```bash
mkdir -p ~/openclaw-mining-demo/{input_docs,outputs,skills/mining-deadlines/bin}
```
Le répertoire depuis lequel tu lances OpenClaw définit implicitement le monde de travail de l’agent.
```bash
cd ~/openclaw-mining-demo
```
puis pour lancer openclaw
```bash
openclaw onboard
```

###
# On verifie qu'on est dans le bon working space
###

OpenClaw utilise un workspace configuré, par défaut ~/.openclaw/workspace. Cette commande permet de verifier ou est le workspace
```bash
openclaw config get agents.defaults.workspace
```
Et donc si on veut changer le workspace, on fait la commande suivante
```bash
openclaw config set agents.defaults.workspace "/home/alexandre/Code/ENSAE/cours_agents_td/openclaw_agents/openclaw-mining-demo"
```
puis il faut updater le gateway
```bash
openclaw gateway restart
```

Attention il peut avoir du mal a changer le workspace.
```bash
openclaw gateway restart
openclaw node restart
```

Et parfois même lorsqu'il dit que le workspace est au bon endroit "/home/alexandre/Code/ENSAE/cours_agents_td/thomas_snippets/openclaw-mining-démo"
en fait il continue à chercher les fichiers dans ~/.openclaw/workspace. Et parfois dans ce cas la, il vaut mieux simplement créer un
lien symbolique de notre dossier vers le dossier auquel il est habitué.

On renomme l’ancien workspace OpenClaw
```bash
mv ~/.openclaw/workspace ~/.openclaw/workspace_backup
```
On crée un lien symbolique pour éviter les problemes
```bash
ln -s /home/alexandre/Code/ENSAE/cours_agent_td/openclaw_agents/openclaw-mining-demo ~/.openclaw/workspace
```
et on oublie pas de restart la gateway
```bash
openclaw gateway restart
openclaw terminal
```

###
# Pour changer un modele dans OpenClaw
### 

```bash
openclaw models list
```

```bash
openclaw config set agents.defaults.model "openai/gpt-4o-mini"
```

```bash
openclaw config get agents.defaults.model
```

```bash
openclaw gateway restart
```

Pour un modele local : 
```bash
ollama pull qwen3.5
ollama launch openclaw --model qwen3.5
```

```bash
openclaw gateway restart
```

###
# Ensuite on lance l'agent
###

On fait `talk to agent` pour passer du crustodian a l'agent qui a acces aux outils que l'on a mis en place.

Le prompt que l'on utilise pour definir l'objectif de l'agent
```bash
Lis le fichier AGENT.md et fait le travail qu'il te demande.
```

```bash
Run this command first:

python skills/mining-deadlines/bin/extract_text.py

Then analyze the generated text files in outputs/text/ one by one.

Do not attempt to read PDF files directly.
```


###
# Debug au cas ou
###

Pour lancer python pour faire cela :
```bash
uv venv
source .venv/bin/activate
uv pip install python-dateutil
```

Pour verifier les elements dans skills.
```bash
find skills -maxdepth 3 -type f
```

On rend les fichiers executables (chmod = change mode, et +x pour les rendre executables). Sinon on ne peut faire que python build_ics.py et pas ./build_ics.py 
```bash
chmod +x skills/mining-deadlines/bin/validate_deadlines.py
chmod +x skills/mining-deadlines/bin/build_ics.py
chmod +x skills/mining-deadlines/bin/extract_text.py
```
Sinon on peut verifier que les fonctions marchent correctement
```
python skills/mining-deadlines/bin/build_ics.py deadlines.csv output.ics
```

On cree un csv dummy de deadlines.csv pour verifier que le tool build_ics.py fonctionne bien :
```bash
cat > outputs/deadlines.csv << 'EOF'
company,project,date,title,category,importance,source_document,source_excerpt,confidence,notes
Example Mining,Demo Mine,2026-09-01,Expected feasibility study completion,Feasibility milestone,High,demo.pdf,"The feasibility study is expected in Q3 2026.",0.75,"Quarter only; approximated to first day of September."
EOF
```

On vérifie que le code fonctionne si on le lance nous-meme : 
```bash
python skills/mining-deadlines/bin/build_ics.py outputs/deadlines.csv outputs/investor_calendar.ics
python skills/mining-deadlines/bin/extract_text.py
```


###
# Analyse des fichiers crées par OpenClaw
### 

Le modèle a créé un certain nombre de fichiers. Dans OpenClaw, ces fichiers structurent le comportement, la mémoire et l’environnement de travail de l’agent. Ils servent de “système d’exploitation” du workspace.
- AGENTS.md = workflow principal
- HEARTBEAT.md = suivi de progression
- IDENTITY.md = Persona de l'agent
- SOUL.md = Principes profonds / philosophie
- TOOLS.md = scripts Python disponibles
- USER.md = objectifs