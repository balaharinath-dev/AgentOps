from typing import TypedDict, List, Dict, Any

class GraphState(TypedDict):
    orchestrator_agent: List[Dict[str, Any]] | None
    push_analyzer_agent: List[Dict[str, Any]] | None
    code_analyzer_agent: List[Dict[str, Any]] | None
    test_generator_agent: List[Dict[str, Any]] | None
    deployment_gateway_agent: List[Dict[str, Any]] | None
    next_agent: str | None