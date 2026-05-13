



## 0. Prepare your work space

This tutorial shows how to use datalab to build a work space for LLM agent.

The OS is a debian 13 server.

### Use local LLM model

To avoid paying LLM model, we will use a local LLM model running by OLLAMA.

```shell
# install ollama
curl -fsSL https://ollama.com/install.sh | sh

# you may need to install some dependencies to succed the installation

# Run ollama in your terminal to open the interactive menu:
ollama

# it will ask you to download some model.

# list all existing model
ollama list
```

> For more details about ollama docs, you can visit this [page](https://docs.ollama.com/quickstart).


### Ollama and gpu

If you have a gpu, you should use it. Normally ollama configure everything for you, if you have installed nvidia cuda driver.

You can use the below steps to check if your ollama really runs o the gpu.

```shell
# show nvidia cuda status
nvidia-smi

# expected output
Mon May 11 08:15:17 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 575.57.08              Driver Version: 575.57.08      CUDA Version: 12.9     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  Tesla T4                       Off |   00000000:86:00.0 Off |                    0 |
| N/A   50C    P8             17W /   70W |       0MiB /  15360MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
                                                                                         
+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+
```

Run a model with ollama, and check with 

```shell
ollama ps

# expected output
gemma4:latest    c6eb396dbd59    10 GB    100% GPU     4096       2 minutes from now 
```

> this output means ollama runs a llm model gemma4 on gpu.


