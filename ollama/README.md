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
# the above command should create a container called ollama
c9dfb3742d6c   ollama/ollama   "/bin/ollama serve"   About a minute ago   Up About a minute   0.0.0.0:11434->11434/tcp, :::11434->11434/tcp   ollama
 
# to enable the gpu, you need to follow the instruction via https://hub.docker.com/r/ollama/ollama

# Run model locally, the below code download and deploy a model called llama3 via ollama in the container ollama

docker exec -it ollama ollama run llama3

# You can also get a prompt of the ollama container
docker exec -it ollama bash
# after the above command, you should have a bash prompt which allow you to run any command

# download a model
ollama pull steamdj/llama3.1-cpu-only

# run a model
ollama run steamdj/llama3.1-cpu-only

# after the run command, you should see a prompt which you can send query to the deployed model.

# the detail of the model can be found here
https://ollama.com/library/llama3
# the model lib for ollama 
https://ollama.com/library
```

## 2. Run ollama on linux

The details install doc can be found [here](https://github.com/ollama/ollama/blob/main/docs/linux.md)

### 2.1 Use the default installation script

In most of the case, the default installation script is enough to have the ollama running

```shell
curl -fsSL https://ollama.com/install.sh | sh

# after installation, start the ollama service
ollama serve
 
# In another terminal, verify that Ollama is running:
ollama -v
```

### 2.2 The detailed manual installation steps

```shell
# 1 Download and extract the package: 
curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz

# 2. untar the package and put it in /usr
sudo tar -C /usr -xzf ollama-linux-amd64.tgz

# start the ollama service
ollama serve
 
# In another terminal, verify that Ollama is running:
ollama -v

```

#### 2.2.1 Adding Ollama as a startup service (recommended)

 **This step is inculed in the default installation script.**
 
```shell
# create user and group for Ollama
sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama
sudo usermod -a -G ollama $(whoami)

# create a service file in /etc/systemd/system/ollama.service
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=$PATH"

[Install]
WantedBy=default.target

#  start the service:
sudo systemctl daemon-reload
sudo systemctl enable ollama
```

## 3. GPU

### 3.1 nvidia GPU
For nvidia GPU, you need to donwload and install the [CUDA](https://developer.nvidia.com/cuda-downloads)

Verify that the drivers are installed by running the following command, which should print details about your GPU:

```shell
nvidia-smi
```

### 3.2 Monitor GPU usage



## 4. Some basic ollama command

```shell
# download a model
ollama pull llama3.2

# run a model, if the model does not exist locally, it will download it first
ollama run llama3

```

> after run, you will get a prompt which can take questions.

## 5. Customize a prompt

https://github.com/ollama/ollama/blob/main/docs/import.md
