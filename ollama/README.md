# Ollama 

Many tutorial for LLMs are using remote models via API. But for dev, we would like to run large language models (LLMs) 
locally. But configuring your working environment and getting LLMs to run on your machine is not trivial.

**Ollama** can be considered as a LLMs model runtime. With Ollama, everything you need to run an LLM model such as
`weights and all of the config` is packaged into a single **Modelfile**. 

You can find the official github page [here](https://github.com/ollama/ollama).

## Run ollama via docker

```shell
# get the image
docker pull ollama/ollama

# run the container with cpu only
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# to enable the gpu, you need to follow the instruction via https://hub.docker.com/r/ollama/ollama


```