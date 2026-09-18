"""Builds the Nishchint LangGraph (spec section 12.2).

START -> understand_complaint -> retrieve_context -> identify_transaction ->
  [FOUND] -> investigate_transaction -> evaluate_policy -> decide_next_action
  [AMBIGUOUS/NOT_FOUND] -> decide_next_action (skips investigation; asks the
    customer instead of hallucinating a transaction)
-> execute_action -> schedule_followup -> write_audit -> generate_response -> END

The sensitive-credential path short-circuits straight from
understand_complaint to generate_response so a secret never reaches the rest
of the pipeline (spec section 29).
"""

from langgraph.graph import END, StateGraph

from app.agent import nodes
from app.agent.state import NishchintState


def _route_after_understand(state: NishchintState) -> str:
    return "generate_response" if state.get("contains_sensitive_credential") else "retrieve_context"


def _route_after_identify(state: NishchintState) -> str:
    return "investigate_transaction" if state.get("transaction_match_status") == "FOUND" else "decide_next_action"


def build_graph():
    graph = StateGraph(NishchintState)

    graph.add_node("understand_complaint", nodes.understand_complaint)
    graph.add_node("retrieve_context", nodes.retrieve_context)
    graph.add_node("identify_transaction", nodes.identify_transaction)
    graph.add_node("investigate_transaction", nodes.investigate_transaction)
    graph.add_node("evaluate_policy", nodes.evaluate_policy)
    graph.add_node("decide_next_action", nodes.decide_next_action)
    graph.add_node("execute_action", nodes.execute_action)
    graph.add_node("schedule_followup", nodes.schedule_followup_node)
    graph.add_node("write_audit", nodes.write_audit)
    graph.add_node("generate_response", nodes.generate_response)

    graph.set_entry_point("understand_complaint")

    graph.add_conditional_edges(
        "understand_complaint",
        _route_after_understand,
        {"generate_response": "generate_response", "retrieve_context": "retrieve_context"},
    )
    graph.add_edge("retrieve_context", "identify_transaction")
    graph.add_conditional_edges(
        "identify_transaction",
        _route_after_identify,
        {"investigate_transaction": "investigate_transaction", "decide_next_action": "decide_next_action"},
    )
    graph.add_edge("investigate_transaction", "evaluate_policy")
    graph.add_edge("evaluate_policy", "decide_next_action")
    graph.add_edge("decide_next_action", "execute_action")
    graph.add_edge("execute_action", "schedule_followup")
    graph.add_edge("schedule_followup", "write_audit")
    graph.add_edge("write_audit", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()


_compiled_graph = None


def get_agent_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
