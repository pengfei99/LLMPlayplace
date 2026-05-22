# Large Language Models (LLM) cours

This course introduces the theory, engineering, and practical applications of `Large Language Models (LLMs)`. It is designed for undergraduate or graduate computer science students with basic knowledge of Python, machine learning, and linear algebra.

The course combines:
- Mathematical foundations 
- Deep learning concepts 
- Transformer architectures 
- LLM training pipelines 
- Prompt engineering 
- Retrieval-Augmented Generation (RAG)
- Fine-tuning techniques 
- AI agents 
- Evaluation and safety 
- Deployment and optimization



Students should know:

- Python programming 
- Data structures and algorithms 
- Basic statistics and probability 
- Linear algebra 
- Machine learning fundamentals 
- Linux command line basics 
- PyTorch basics (better to have) 
- NLP fundamentals (better to have)

By the end of the course, students will be able to:

- Explain how modern LLMs work internally
- Implement transformer components in PyTorch
- Train small language models
- Use tokenization and embeddings effectively
- Apply prompt engineering techniques
- Build Retrieval-Augmented Generation systems
- Fine-tune models using LoRA and QLoRA
- Evaluate LLM quality and limitations
- Design AI agents and tool-using systems
- Deploy optimized LLM applications
- Understand safety, bias, and alignment challenges

## Lecture 1 — Introduction to AI, NLP, and LLMs

Topics:
- History of AI 
- Evolution of NLP 
- Rule-based systems vs statistical NLP 
- Deep learning revolution 
- Emergence of transformers 
- What is an LLM? 
- Decoder-only vs encoder-decoder models 
- Open-source vs proprietary models 
- Lecture Content

NLP Historical Timeline:
- ELIZA 
- Statistical language models 
- Word2Vec 
- Seq2Seq models 
- Attention mechanism 
- Transformer architecture 
- GPT family 
- Modern reasoning models

Main Applications of LLMs:
- Chatbots 
- Code generation 
- Translation 
- Search augmentation 
- Summarization 
- AI agents 
- Scientific assistants

TP:
- Install Python environment 
- Install PyTorch 
- Use Hugging Face Transformers 
- Run first inference with a small model

## Lecture 2 — Mathematics for LLMs
Topics:
- Vectors and matrices 
- Matrix multiplication 
- Eigenvalues intuition 
- Gradients and derivatives 
- Probability distributions 
- Softmax 
- Cross entropy loss 
- Optimization basics

Key Concepts:
- Vector Embeddings : Represent words or tokens as vectors in high-dimensional spaces.
- Gradient Descent : Optimization algorithm used to train neural networks.
- Cross Entropy : Measures prediction error between expected and predicted token probabilities.

TP: Use `NumPy` to implement:
- Softmax 
- Cross entropy 
- Gradient descent

## Lecture 3 — Neural Networks and Deep Learning Foundations
Topics:
- Perceptrons 
- Feed-forward neural networks 
- Activation functions 
- Backpropagation 
- GPU acceleration 
- Training loops

Key Concepts
- Activation Functions (e.g. ReLU, GELU, Sigmoid, Tanh,
- Training Challenges (Vanishing gradients, Overfitting, Underfitting)

TP: Train a simple text classifier using PyTorch.

## Lecture 4 — Tokenization and Embeddings
Topics:
- Text preprocessing 
- Vocabulary construction 
- Byte Pair Encoding (BPE)
- SentencePiece 
- Word embeddings 
- Positional embeddings

Key Concepts:
- Text to tokens(vectors): Language models process tokens instead of raw text.
- Use vectors to build a Embedding Spaces/universe: Semantic similarity emerges in vector spaces.

TP: 
- Build a tokenizer
- Visualize embeddings
- Use t-SNE or PCA
- Compare: Character tokenization, Word tokenization, Subword tokenization

## Lecture 5 — Attention Mechanism and Transformers

Topics:
- Sequence modeling problems 
- Self-attention 
- Query, Key, Value 
- Multi-head attention 
- Transformer blocks 
- Residual connections 
- Layer normalization 

Key Concepts 
- Self-Attention: Allows the model to dynamically focus on relevant tokens.
- Transformer Advantages: Parallelization, Long-range dependency modeling, Scalability

TP: 
- Implement scaled dot-product attention in PyTorch.
- Implement a mini transformer encoder.


## Lecture 6 — Generative Language Models
Topics:
- Autoregressive generation
- Causal masking
- Decoder-only transformers
- GPT architecture
- Sampling methods

Key Concepts:
- Sampling Techniques: Greedy decoding, Beam search, Top-k sampling, Top-p sampling, Temperature scaling

TP:
- Generate text with different decoding strategies.
- Analyze output diversity with different temperatures.

## Lecture 7 — LLM Training Pipeline
Topics:
- Dataset collection
- Data cleaning
- Pretraining objectives
- Distributed training
- GPUs and TPUs
- Checkpoints
- Scaling laws

Key Concepts
- Pretraining : Models learn next-token prediction over massive datasets.
- Scaling Laws (Performance improves with: `More parameters`, `More data`,`More compute`)

TP:
- Train a tiny language model on a custom dataset.
- Estimate memory usage for different model sizes.

## Lecture 8 — Prompt Engineering
Topics:
- Prompt design 
- Zero-shot prompting 
- Few-shot prompting 
- Chain-of-thought prompting 
- System prompts 
- Structured outputs

Key Concepts
- Prompt Patterns 
    - Role prompting 
    - Reasoning prompts 
    - Step-by-step prompting 
    - Instruction formatting

TP:
- Create prompts for:
   - Summarization 
   - Code generation 
   - Classification 
   - Information extraction
- Optimize prompts for a specific benchmark task.

## Lecture 9 — Retrieval-Augmented Generation (RAG)
Topics:
- Vector databases 
- Embedding models 
- Semantic search 
- Chunking strategies 
- Retrieval pipelines 
- Hybrid search

Key Concepts:
- Why RAG? 
 - LLMs cannot reliably memorize all knowledge.
 - RAG enables:
   - Fresh information 
   - Private document search 
   - Reduced hallucinations

- Architecture
  1. User query 
  2. Embedding generation 
  3. Vector search 
  4. Context retrieval 
  5. Prompt augmentation 
  6. LLM response

TP:

- Build a simple RAG chatbot using `FAISS, Sentence Transformers, Open-source LLM`.
- Compare chunking strategies.

## Lecture 10 — Fine-Tuning and Adaptation

Topics: 
- Supervised fine-tuning 
- Instruction tuning 
- Parameter-efficient tuning: LoRA, QLoRA, Adapters, Quantization

Key Concepts
- LoRA: Fine-tunes small low-rank matrices instead of the full model.
- Quantization: Reduces model memory usage.

TP
- Fine-tune a small model using LoRA.
- Compare full fine-tuning vs LoRA.

## Lecture 11 — AI Agents and Tool Use
Topics:
- What is an AI agent?
- LLM orchestration
- Function calling
- Tool usage
- Planning systems
- Memory systems
- Multi-agent systems

Key Concepts
- Agent Architecture(Typical components):
  - LLM reasoning core
  - Memory 
  - Planning 
  - External tools 
  - Execution engine
- Agent Examples
  - Coding assistants 
  - Research agents 
  - Autonomous workflows

TP:
- Build an agent capable of: Searching documents, Using tools, Producing reports
- Design an architecture for an enterprise AI agent

## Lecture 12 — Evaluation and Safety
Topics
- Hallucinations 
- Bias 
- Toxicity 
- Jailbreak attacks 
- Red teaming 
- Benchmarking 
- Human evaluation 

Key Concepts
- Evaluation Metrics 
  - Perplexity 
  - BLEU 
  - ROUGE 
  - Human preference
- Aligning models with human expectations.

TP:
- Evaluate model responses using benchmark datasets.
- Analyze failure cases in generated outputs.

## Lecture 13 — Deployment and Optimization
Topics
- Model serving 
- GPU inference 
- Quantized inference 
- vLLM 
- TensorRT 
- ONNX 
- Caching 
- Throughput optimization

Key Concepts:
- Inference Optimization 
  - KV cache 
  - Continuous batching 
  - Quantization 
  - Speculative decoding

TP:
- Deploy a chatbot API locally.
- Benchmark latency and throughput.

## Lecture 14 — Future of LLMs and Final Presentations
Topics:
- Multimodal AI 
- Reasoning models 
- Autonomous systems 
- Long-context models 
- Open research problems 
- AI governance

## Extra info
Vector Databases
- FAISS 
- Chroma 
- Milvus

Model Families
- GPT 
- Llama 
- Mistral
- Gemma 
- DeepSeek