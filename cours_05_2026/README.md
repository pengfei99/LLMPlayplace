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

### No live data(can't execute action)

LLM does not have access of live data, and it can not execute an `action`
(e.g. list files in a directory, search a keyword in a web page, etc.) to retrieve live data. So it only has the 
knowledge which training data provides. 


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
> 

## 3. Memory for LLM and Agent

LLM model does not `have memory` of previous user input. Users need to prepare all the information and inject them as `context
of the query` and sent all to the LLM.

Agent can have two types memory:
- short-term memory: Conversation context(e.g. previous llm output messages, temporary variables, current task state) 
- long-term memory: Persistent knowledge (e.g. user preferences, existing docs, history decisions) often stores in a RAG or db.

> The definition of short/long memory are not official standards, but a naming convention of the IA domain.
> 

## 4. Actions/Tools

Tools are what make an agent useful. With tools, agent can interact with systems which LLM does not have access.

For example, below are some popular tools
- Web search: Retrieve information
- Python execution: Compute/analyze
- Database access: Query data
- Email API: Send emails

## 5. Planning and reasoning

A major feature of agents is decomposition(i.e. divide one task complexe to multiple simple tasks).

For example, `analyze failed spark jobs and summarize root causes`

A possible workflow for agent:
1. Query spark job logs
2. Filter error logs
3. Analyze error logs and detect causes
4. Generate error report
5. Suggest remediation

## 6. Agent feedback loops

As the reponse of LLM is non-deterministic, we are not sure if we can obtain what we want with 1 pass of the agent workflow.

We ofen has a control step which controls the output of the LLM or the tools called by LLM.

If the control pass, return the response, if not, ask agent to repeat the workflow.


## 7. Different types of AI agents

- Simple reactive agents: no memory, no tool, just user input -> llm output
- Tool using agents: agent can call tools to archive objectives
- Autonomous agents: Operate for extended periods with limited supervision. e.g. automated trading systems 
- Multi-agent systems: Several agents collaborate to archive objectives.


## 8. Common agent architecture

ReAct :




