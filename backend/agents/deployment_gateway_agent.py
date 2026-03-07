import warnings
warnings.filterwarnings("ignore")

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from prompts.deployment_gateway_prompt import DEPLOYMENT_GATEWAY_SYSTEM_PROMPT as SYSTEM_PROMPT
from tools.deployment_gateway_tools import create_jira_story_with_tasks, store_deployment_decision

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
    tools=[create_jira_story_with_tasks, store_deployment_decision]
)

def deployment_gateway_agent(state: GraphState):
    # Get all previous reports
    push_analysis_output = state.get("push_analyzer_agent", [])
    push_analysis_report = push_analysis_output[-1].get("push_analysis_report", "") if push_analysis_output else "No report available"
    
    code_analysis_output = state.get("code_analyzer_agent", [])
    code_analysis_report = code_analysis_output[-1].get("code_analysis_report", "") if code_analysis_output else "No report available"
    
    test_generation_output = state.get("test_generator_agent", [])
    test_generation_report = test_generation_output[-1].get("test_generation_report", "") if test_generation_output else "No report available"
    
    orchestrator_output = state.get("orchestrator_agent", [])
    orchestrator_validations = "\n\n".join([
        f"Validation {idx+1}:\n{val.get('validation', '')}" 
        for idx, val in enumerate(orchestrator_output)
    ]) if orchestrator_output else "No validations available"
    
    # Get workflow identifiers
    workflow_run_id = state.get("workflow_run_id", "unknown")
    commit_id = state.get("commit_id", "unknown")
    repo_path = state.get("repo_path", os.getenv('TEST_ENV_PATH', 'unknown'))
    
    # Build the query with all reports
    query = f"""
    Make the final deployment decision based on all agent reports and validations.

    Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    Repository: {repo_path}
    Workflow Run ID: {workflow_run_id}
    Commit ID: {commit_id}

    PUSH ANALYZER REPORT:
    {push_analysis_report}

    CODE ANALYZER REPORT:
    {code_analysis_report}

    TEST GENERATOR REPORT:
    {test_generation_report}

    ORCHESTRATOR VALIDATIONS:
    {orchestrator_validations}

    CRITICAL INSTRUCTIONS:
    1. Review ALL reports and validations thoroughly
    2. Evaluate deployment readiness based on decision criteria
    3. Make DEPLOY or BLOCK decision
    4. If BLOCK: Create Jira ticket with committer as assignee
    5. Store deployment decision in database using workflow_run_id: {workflow_run_id}, commit_id: {commit_id}, repo_path: {repo_path}
    6. Generate comprehensive production-level deployment report with detailed diff analysis

    IMPORTANT: Include a comprehensive DIFF ANALYSIS section in your report that covers:
    - All changed files with their modifications
    - Code additions and deletions
    - Function/class changes
    - Dependency changes
    - Configuration changes
    - Impact of each change

    Follow your workflow:
    - Analyze all reports
    - Evaluate deployment readiness
    - Make deployment decision
    - Handle BLOCK status (create Jira ticket if needed)
    - Store decision in database
    - Generate final report with comprehensive diff analysis

    Proceed dynamically.
    """

    response = agent.invoke({"messages": [{"role": "user", "content": query}]})

    print("\n" + "="*80)
    print(" "*25 + "DEPLOYMENT GATEWAY REPORT")
    print("="*80 + "\n")

    # Extract and print the report
    report_content = response.get("messages")[-1].content
    if isinstance(report_content, list):
        # Handle list format from the response
        for content_block in report_content:
            if isinstance(content_block, dict) and "text" in content_block:
                print(content_block["text"])
            else:
                print(content_block)
    else:
        # Handle string format
        print(report_content)

    print("\n" + "="*80)
    print(" "*30 + "END OF REPORT")
    print("="*80 + "\n")

    state["deployment_gateway_agent"] = state.get("deployment_gateway_agent", [])
    state["deployment_gateway_agent"].append({"deployment_report": report_content})
    
    return state
