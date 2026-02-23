import warnings
warnings.filterwarnings("ignore")

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from prompts.code_analyzer_prompt import CODE_ANALYZER_SYSTEM_PROMPT as SYSTEM_PROMPT
from tools.code_analyzer_tools import (
    execute_cli_commands, 
    analyze_python_ast, 
    build_dependency_graph,
    detect_cycles,
    compute_metrics
)

from state.state import GraphState

from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

model = ChatGoogleGenerativeAI(
    project=os.getenv("GCP_PROJECT_NAME"),
    model="gemini-2.5-flash",
    temperature=0
)

agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[execute_cli_commands, analyze_python_ast, build_dependency_graph, detect_cycles, compute_metrics]
)

def code_analyzer_agent(state: GraphState):
    # Get the push analyzer report
    push_analysis_output = state.get("push_analyzer_agent", [])
    push_analysis_report = push_analysis_output[-1].get("push_analysis_report", "") if push_analysis_output else "No report available"
    
    # Check if there's a recommendation from orchestrator for rework
    orchestrator_output = state.get("orchestrator_agent", [])
    orchestrator_recommendation = ""
    
    if orchestrator_output:
        last_orchestrator_feedback = orchestrator_output[-1].get("validation", "")
        orchestrator_recommendation = f"""

    ORCHESTRATOR FEEDBACK (Rework Required):
    {last_orchestrator_feedback}

    Please address the above feedback and improve your analysis accordingly.
    """
        
        # Build the query with push analyzer report and orchestrator recommendation
        query = f"""
    Perform comprehensive code analysis based on the push analyzer report.

    Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    Repository: {os.getenv('TEST_ENV_PATH', 'Not specified')}

    PUSH ANALYZER REPORT:
    {push_analysis_report}
    {orchestrator_recommendation}
    Using the above report:
    1. Extract the list of changed files
    2. Perform project-level analysis using CLI commands
    3. Analyze each changed file in detail (classes, functions, imports)
    4. Build dependency graph and detect issues
    5. Identify quality flags and concerns
    6. Generate comprehensive structured report

    Analyze at all levels: Project, File, Class, Function, Dependency, Quality.

    Proceed dynamically.
    """

    response = agent.invoke({"messages": [{"role": "user", "content": query}]})

    print("\n" + "="*80)
    print(" "*25 + "CODE ANALYSIS REPORT")
    print("="*80 + "\n")

    # Extract and print the analysis
    analysis_content = response.get("messages")[-1].content
    if isinstance(analysis_content, list):
        # Handle list format from the response
        for content_block in analysis_content:
            if isinstance(content_block, dict) and "text" in content_block:
                print(content_block["text"])
            else:
                print(content_block)
    else:
        # Handle string format
        print(analysis_content)

    print("\n" + "="*80)
    print(" "*30 + "END OF REPORT")
    print("="*80 + "\n")

    state["code_analyzer_agent"] = state.get("code_analyzer_agent", [])
    state["code_analyzer_agent"].append({"code_analysis_report": analysis_content})
    
    return state