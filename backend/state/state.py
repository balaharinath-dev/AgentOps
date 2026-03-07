from typing import TypedDict, List, Dict, Any, Annotated
from operator import add

class GraphState(TypedDict):
    orchestrator_agent: Annotated[List[Dict[str, Any]], add]
    push_analyzer_agent: Annotated[List[Dict[str, Any]], add]
    code_analyzer_agent: Annotated[List[Dict[str, Any]], add]
    test_generator_agent: Annotated[List[Dict[str, Any]], add]
    deployment_gateway_agent: Annotated[List[Dict[str, Any]], add]
    next_agent: str | None
    workflow_run_id: str | None  # UUID string
    commit_id: str | None  # Git commit ID
    repo_path: str | None  # Repository path