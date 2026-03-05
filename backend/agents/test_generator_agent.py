import warnings
warnings.filterwarnings("ignore")

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from prompts.test_generator_prompt import TEST_GENERATOR_SYSTEM_PROMPT as SYSTEM_PROMPT
from tools.test_generator_tools import explore_test_history, execute_tests

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
    tools=[explore_test_history, execute_tests]
)

def test_generator_agent(state: GraphState):
    # Get the push analyzer report
    push_analysis_output = state.get("push_analyzer_agent", [])
    push_analysis_report = push_analysis_output[-1].get("push_analysis_report", "") if push_analysis_output else "No report available"
    
    # Get the code analyzer report
    code_analysis_output = state.get("code_analyzer_agent", [])
    code_analysis_report = code_analysis_output[-1].get("code_analysis_report", "") if code_analysis_output else "No report available"
    
    # Check if there's a recommendation from orchestrator for rework
    orchestrator_output = state.get("orchestrator_agent", [])
    orchestrator_recommendation = ""
    
    if orchestrator_output:
        last_orchestrator_feedback = orchestrator_output[-1].get("validation", "")
        orchestrator_recommendation = f"""

    ORCHESTRATOR FEEDBACK (Rework Required):
    {last_orchestrator_feedback}

    Please address the above feedback and improve your test generation accordingly.
    """
    
    # Build the query with all previous reports
    query = f"""
    Generate comprehensive test suite ONLY for changed files and their direct dependents.

    Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    Repository: {os.getenv('TEST_ENV_PATH', 'Not specified')}

    PUSH ANALYZER REPORT:
    {push_analysis_report}

    CODE ANALYZER REPORT:
    {code_analysis_report}
    {orchestrator_recommendation}
    
    CRITICAL INSTRUCTIONS:
    - Extract the list of CHANGED files from push analyzer report
    - Extract the list of DEPENDENT files from dependency analysis
    - Generate tests ONLY for these files - DO NOT test unchanged code
    - Focus testing effort on the specific changes made in this push
    
    Using the above reports:
    1. Query test history database to learn from past failures (for changed files only)
    2. Identify changed files and their direct dependents
    3. Generate appropriate test scripts ONLY for changed/dependent files (Unit, API, Database, Validation, etc.)
    4. Store test scripts in database
    5. Execute all generated tests
    6. Capture results and coverage data (for changed files only)
    7. Generate comprehensive test report

    Follow your workflow:
    - Explore test history first (for changed files)
    - Generate tests by priority (P1 > P2 > P3) for changed/dependent files only
    - Execute tests and store results
    - Provide detailed report with recommendations

    Proceed dynamically.
    """

    response = agent.invoke({"messages": [{"role": "user", "content": query}]})

    print("\n" + "="*80)
    print(" "*25 + "TEST GENERATION REPORT")
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

    state["test_generator_agent"] = state.get("test_generator_agent", [])
    state["test_generator_agent"].append({"test_generation_report": analysis_content})
    
    return state
