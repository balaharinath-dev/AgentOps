import warnings

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
)

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from agents.orchestrator_agent import orchestrator_agent
from agents.push_analyzer_agent import push_analyzer_agent
from agents.code_analyzer_agent import code_analyzer_agent

from state.state import GraphState

def route_decision(state: GraphState) -> Literal["push_analyzer_agent", "code_analyzer_agent", "__end__"]:
    """Route based on orchestrator's decision"""
    next_agent = state.get("next_agent", "")
    
    # Parse orchestrator output to find NEXT_AGENT
    if isinstance(next_agent, str):
        if "push_analyzer" in next_agent.lower():
            return "push_analyzer_agent"
        elif "code_analyzer" in next_agent.lower():
            return "code_analyzer_agent"
        # Add more agent routing as you build them
        # elif "test_generator" in next_agent.lower():
        #     return "test_generator_agent"
    
    # Default: end the workflow
    return "__end__"

build = StateGraph(GraphState)

build.add_node("orchestrator_agent", orchestrator_agent)
build.add_node("push_analyzer_agent", push_analyzer_agent)
build.add_node("code_analyzer_agent", code_analyzer_agent)
# Add more agent nodes as you build them
# build.add_node("test_generator_agent", test_generator_agent)

build.add_edge(START, "push_analyzer_agent")
build.add_edge("push_analyzer_agent", "orchestrator_agent")
build.add_edge("code_analyzer_agent", "orchestrator_agent")

# Conditional routing from orchestrator based on its decision
build.add_conditional_edges("orchestrator_agent", route_decision)

checkpointer = InMemorySaver()
graph = build.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    result = graph.invoke(
        {
            "orchestrator_agent": [], 
            "push_analyzer_agent": [],
            "code_analyzer_agent": [],
            "next_agent": None
        }, 
        {"configurable": {"thread_id": "1"}}
    )
    
    print("\n" + "="*80)
    print(" "*30 + "WORKFLOW COMPLETE")
    print("="*80)