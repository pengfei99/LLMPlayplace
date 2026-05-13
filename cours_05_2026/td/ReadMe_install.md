# Instructions d'installation

## Environment set up

```bash
python -m venv env
source env/bin/activate
pip install openai
pip install faiss-cpu
pip install requests
pip install pymupdf4llm
pip install -U langgraph langchain-openai langchain-core
pip install langchain-mcp-adapters mcp-server-sqlite
```

## 

Placer les dossiers de donnees dans un folder data selon la structure suivante : 
data/
├── data/
├── data_rte/
├── data_securite/
├── data_v0/
└── data_v1/


## Utiliser ollama

```bash
sudo apt-get update
sudo apt-get install zstd
curl -fsSL https://ollama.com/install.sh | sh
nohup ollama serve & # runs in background
```

Pour installer un modèle avec Ollama, faire :

```bash
ollama pull qwen3.5:9b
```
ou un modele plus leger
```bash
ollama pull qwen3.5:0.8b
```

Et pour le supprimer :

```bash
ollama rm qwen3.5:9b
```

Pour afficher la liste des modèles installés, on peut faire :

```bash
ollama list
```

Et pour tester ce modèle :

```bash
ollama run qwen3.5:9b
```


## Installation de `tesseract` sur Onyxia (pour le parsing de PDFs)

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-eng
```

## Utiliser et installer vLLM 
```bash
uv pip install vllm
```
Le lancer avec un modele via le terminal :
```bash
python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-7B-Instruct
```
Si le modèle ne tient pas entièrement dans la VRAM du GPU, on peut ajuster le paramètre gpu-memory-utilization (et éventuellement utiliser l’offloading CPU) afin qu’une
partie des ressources nécessaires à l’inférence soit gérée hors GPU. Cela permet d’exécuter des modèles plus volumineux, mais au prix d’une baisse des performances et
d’une latence plus élevée.
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --gpu-memory-utilization 0.80
```bash
ou alors on peut prendre un plus petit modele biensur
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --gpu-memory-utilization 0.70 \
  --max-model-len 8192
```

Et sinon disponible localement sur
```bash
http://localhost:8000/v1
```