# Cours LLM with agent

In this cours, we will learn what is an agent, what is the use case of agent, how to develop an agent.

## 1. LLM is great but has limit

A normal LLM interaction with user is usually:

```text
User -> Prompt -> LLM -> Response
```

### No memory
An LLM only generates response based on user input (context and query) in one single-step. The LLM does not have `memory`,
if user wants the LLM takes into account of previous output of LLM, the user must append the output in the context
of the prompt.

### No action

LLM can execute real world action(e.g. list files in a directory, search a keyword in a web page, etc.).


### No planing(workflow)

LLM is usually single-step, can't react based on its own output

> ChatGPT is not a LLM, it's a multi-agent system which contains multiple LLMs.

## 2. What is an AI agent?

To overcome all the above problems, we need a tool which adds below features on top of the LLM models:
- memory
- planning
- actions/tools
- iterative reasoning
- feedback loops

An **AI agent** is a `software system` that can `perceive, reason, decide, and act` toward a goal with `some degree of autonomy`.

### LLM query vs Agent query

For LLM, you can only get information

```text
What is the weather in Paris?
```
> The model guesses the weather unless connected to tools to get real weather.

For Agent, you can ask it to run a task for you

```text
Check the weather in Paris, if it rains book me a taxi.
```

Agent workflow after user query:
1. Parse query and detects intent(e.g. get weather, book taxi)
2. Calls a tool which query weather API
3. Reads result returned by the tool
4. Reasoning based on the user input rule: if rain -> book taxi
5. Calls a tool to book API, confirms booking
6. send booking info to user.

> You can notice this agent has a complete workflow to fulfil the goal of a user.

### General workflow of Agent

The below graph shows a general workflow of an AI Agent

```text
Parse user query to get the goal
  ↓
Reasoning
  ↓
Choose action
  ↓
Use tools / APIs / code
  ↓
Observe result
  ↓
Decide next step
  ↓
Repeat until goal completed
```

> You often need a `guard`(e.g. after 10 try stop the loop) to avoid infinit loop of an Agent. 