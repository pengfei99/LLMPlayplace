##
# D'abord on s'assure d'avoir un modele en local
##

Pour verifier les modèles déja installés avec ollama
```bash
curl http://localhost:11434/v1/models
```
Et sinon on en installe et run avec la commande suivante
```bash
ollama run qwen3:30b
```


##
# Ensuite on installe OpenCode et on connecte au modèle local via ollama
## 

D'abord on installe OpenCode 
```bash
sudo npm install -g opencode-ai
# curl -fsSL https://opencode.ai/install | bash
```
Et on vérifie que c'est installé avec
```bash
opencode --version
```
et pour savoir à quels modeles opencode a acces on fait
```bash
opencode models
```
Et dans ce runtime agentic (ce gestionnaire de LLM), on veut lui exposer notre modèle local, par exemple :
```bash
vim ~/.config/opencode/opencode.json
```
et rajouter la chose suivante :
```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": {
        "baseURL": "http://localhost:11434/v1"
      },
      "models": {
        "qwen3:30b": {
          "name": "Qwen3 30B via Ollama"
        }
      }
    }
  }
}
```

##
# Ensuite on installe et lance paperclipai
## 

Ensuite on passe a node (pour executer du JavaScript en dehors du navigateur) et a npm (Node Package Manager)
```bash
node --version   # >= 20
npm install -g pnpm
pnpm --version   # >= 9.15
```

Ensuite on fait l'onboarding
```bash
npx paperclipai onboard --yes
```
qui cree une section locale qui cree une session sur http://localhost:3100


##
# Evoluer avec paperclipai
## 

On peut supprimer une session de cette maniere
```
rm -rf ~/.paperclip/instances/default/db
npx paperclipai run
```
