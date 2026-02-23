import warnings
warnings.filterwarnings("ignore")

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from prompts.push_analyzer_prompt import PUSH_ANALYZER_SYSTEM_PROMPT as SYSTEM_PROMPT
from tools.push_analyzer_tools import execute_git_commands, analyze_file_dependencies

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
    tools=[execute_git_commands, analyze_file_dependencies]
)

def push_analyzer_agent(state: GraphState):
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
    
    # Build the query with or without orchestrator recommendation
    query = f"""
    Analyze the latest push to the repository.

    Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    Repository: {os.getenv('TEST_ENV_PATH', 'Not specified')}
    {orchestrator_recommendation}
    Perform your analysis following your workflow:
    1. Start with git pull and gather commit information
    2. Identify changed files
    3. Analyze dependencies for the changed files
    4. Generate comprehensive structured report

    Proceed dynamically.
"""

    response = agent.invoke({"messages": [{"role": "user", "content": query}]})

    print("\n" + "="*80)
    print(" "*25 + "GIT PUSH ANALYSIS REPORT")
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

    state["push_analyzer_agent"] = state.get("push_analyzer_agent", [])
    state["push_analyzer_agent"].append({"push_analysis_report": analysis_content})
    
    return state