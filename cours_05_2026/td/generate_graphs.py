"""
This script is used to generate the graph of the agent.

You need to have graphviz installed.
You can install it with the following command:
```bash
pip install graphviz
```

You can then run the script with the following command:
python generate_graphs.py
"""

from pathlib import Path

from graphviz import Digraph

OUTPUT_DIR = Path("files/examples_graphs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def render_graph(dot: Digraph, filename: str) -> None:
    path = OUTPUT_DIR / filename
    rendered_path = dot.render(str(path), format="png", cleanup=True)
    print(f"Graph generated successfully in {rendered_path}")


def graph_cours():
    dot = Digraph()

    dot.attr(rankdir="TB")

    dot.node("START", "START", shape="oval")
    dot.node("call_model", "call_model", shape="box")
    dot.node("execute_tools", "execute_tools", shape="box")
    dot.node("too_many_tools", "too_many_tools", shape="box")
    dot.node("END", "END", shape="oval")

    dot.edge("START", "call_model")

    dot.edge("call_model", "execute_tools", label="tools")
    dot.edge("call_model", "END", label="final")
    dot.edge("call_model", "too_many_tools", label="too_many_tools")

    dot.edge("execute_tools", "call_model")
    dot.edge("too_many_tools", "END")

    dot.render("files/examples_graphs/graph", format="png", cleanup=True)
    print("Graph generated successfully in files/examples_graphs/graph.png")


def graph_exercice_1_router_rag():
    dot = Digraph()

    dot.attr(rankdir="TB")

    dot.node("START", "START", shape="oval")
    dot.node("classify", "classify_request", shape="box")
    dot.node("answer_directly", "answer_directly", shape="box")
    dot.node("retrieve_documents", "retrieve_documents", shape="box")
    dot.node("answer_with_context", "answer_with_context", shape="box")
    dot.node("fallback", "fallback_answer", shape="box")
    dot.node("END", "END", shape="oval")

    dot.edge("START", "classify")

    dot.edge("classify", "answer_directly", label="simple")
    dot.edge("classify", "retrieve_documents", label="needs_docs")
    dot.edge("classify", "fallback", label="out_of_scope")

    dot.edge("retrieve_documents", "answer_with_context")
    dot.edge("answer_directly", "END")
    dot.edge("answer_with_context", "END")
    dot.edge("fallback", "END")

    render_graph(dot, "exercise_1_router_rag")


def graph_exercice_2_rag_check():
    dot = Digraph()

    dot.attr(rankdir="TB")

    dot.node("START", "START", shape="oval")
    dot.node("retrieve", "retrieve_documents", shape="box")
    dot.node("call_model", "call_model", shape="box")
    dot.node("check", "check_answer", shape="box")
    dot.node("fallback", "fallback_answer", shape="box")
    dot.node("END", "END", shape="oval")

    dot.edge("START", "retrieve")
    dot.edge("retrieve", "call_model")
    dot.edge("call_model", "check")

    dot.edge("check", "END", label="good_enough")
    dot.edge("check", "fallback", label="not_enough_context")

    dot.edge("fallback", "END")

    render_graph(dot, "exercise_2_rag_check")


def graph_exercice_3_research_assistant():
    dot = Digraph()

    dot.attr(rankdir="TB")

    dot.node("START", "START", shape="oval")
    dot.node("generate_query", "generate_query", shape="box")
    dot.node("search_documents", "search_documents", shape="box")
    dot.node("evaluate_context", "evaluate_context", shape="box")
    dot.node("route", "_route_after_context_evaluation", shape="diamond")
    dot.node("reformulate_query", "reformulate_query", shape="box")
    dot.node("write_answer", "write_answer", shape="box")
    dot.node("fallback_answer", "fallback_answer", shape="box")
    dot.node("END", "END", shape="oval")

    dot.edge("START", "generate_query")
    dot.edge("generate_query", "search_documents")
    dot.edge("search_documents", "evaluate_context")
    dot.edge("evaluate_context", "route")

    dot.edge("route", "write_answer", label="sufficient")
    dot.edge("route", "reformulate_query", label="insufficient")
    dot.edge("route", "fallback_answer", label="too_many_attempts")

    dot.edge("reformulate_query", "search_documents")
    dot.edge("write_answer", "END")
    dot.edge("fallback_answer", "END")

    render_graph(dot, "exercise_3_research_assistant")


def graph_bonus_email_human_review():
    dot = Digraph()

    dot.attr(rankdir="TB")

    dot.node("START", "START", shape="oval")
    dot.node("draft_email", "draft_email", shape="box")
    dot.node("check_sensitivity", "check_sensitivity", shape="box")
    dot.node("human_review", "human_review", shape="box")
    dot.node("revise_email", "revise_email", shape="box")
    dot.node("END", "END", shape="oval")

    dot.edge("START", "draft_email")
    dot.edge("draft_email", "check_sensitivity")

    dot.edge("check_sensitivity", "END", label="not_sensitive")
    dot.edge("check_sensitivity", "human_review", label="sensitive")

    dot.edge("human_review", "END", label="approved")
    dot.edge("human_review", "revise_email", label="rejected")
    dot.edge("human_review", "END", label="too_many_rejections")

    dot.edge("revise_email", "check_sensitivity")

    render_graph(dot, "bonus_email_human_review")


if __name__ == "__main__":
    graph_cours()
    graph_exercice_1_router_rag()
    graph_exercice_2_rag_check()
    graph_exercice_3_research_assistant()
    graph_bonus_email_human_review()
