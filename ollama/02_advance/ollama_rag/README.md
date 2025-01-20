# Ollama and simple RAG 

In this tutorial, we will use ollama and simple RAG

## Introduction

Before we explore the **Retrieval-Augmented Generation (RAG)** process in detail, it’s essential to understand 
three foundational components: 
 - Vectors: Vectors are `numerical representations of data points that capture their semantic meaning`. In RAG, 
             text documents or queries are transformed into vector embeddings using models like SentenceTransformers. 
             These embeddings enable similarity searches, allowing the system to identify documents that are 
              closest in meaning to a given query.
 - ChromaDB: ChromaDB is an open-source, `AI-native vector database` designed for storing and searching large sets 
             of vector embeddings. Known for its scalability and efficiency, it integrates seamlessly with Python, 
              making it a preferred choice for implementing RAG.
               For more details, visit [ChromaDB’s official site](https://www.trychroma.com/).
 - Ollama: A framework `provides a flexible environment for running, modifying, and managing various large language models`
           (LLMs), including models like Llama, Phi, and others optimized for diverse tasks.

## General workflow

The RAG workflow used in this article can be summarized in four key stages:

1. Indexing: `Data is processed and indexed in ChromaDB` to enable efficient retrieval. This involves converting 
               the data into embeddings using a model and storing these embeddings in the ChromaDB vector database. 
               These embeddings serve as compact, semantic representations for similarity searches.
2. Retrieval: When a user submits a query, the system `performs a similarity search within ChromaDB` to retrieve the 
              most relevant documents or contextual information from the indexed data.
3. Augmentation: `The retrieved information is combined with the user’s query` to create an augmented input. 
               This enriched context provides the LLM with additional details, enabling it to produce more precise 
               and contextually relevant responses.
4. Generation: Using the augmented input, the LLM generates a response that integrates both the additional context 
              and its pre-trained knowledge.