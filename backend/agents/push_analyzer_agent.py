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
    # Convert TypedDict to regular dict for mutability
    state = dict(state)
    
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
    
    # Create workflow_run in database if not already created
    if not state.get("workflow_run_id"):
        try:
            import sys
            backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)
            
            from database.operations import create_workflow_run
            
            # Extract commit info from analysis (parse the report)
            # Convert to string if it's a list
            import re
            report_text = str(analysis_content)
            if isinstance(analysis_content, list):
                # Handle list format - extract text from dict items
                text_parts = []
                for item in analysis_content:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    else:
                        text_parts.append(str(item))
                report_text = ' '.join(text_parts)
            
            # Extract commit hash - look for patterns like "Commit Hash: 8d497ce" or "**Commit Hash**: `8d497ce`"
            commit_match = re.search(r'(?:commit\s*hash|commit)[:\s*`]+([a-f0-9]{7,40})', report_text, re.IGNORECASE)
            commit_id = commit_match.group(1) if commit_match else "unknown"
            
            # Extract committer email - look for email pattern
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', report_text)
            committer_email = email_match.group(0) if email_match else None
            
            # Extract committer name - look for patterns like "Author: balaharinath.dev" or "**Author**: `balaharinath.dev`"
            name_match = re.search(r'(?:author|committer)[:\s*`]+([^<\n`*]+?)(?:`|\n|$)', report_text, re.IGNORECASE)
            committer_name = name_match.group(1).strip() if name_match else None
            
            # Extract branch - look for patterns like "Branch: main" or "**Branch**: `main`"
            branch_match = re.search(r'(?:branch)[:\s*`]+([^\n`*]+?)(?:`|\n|$)', report_text, re.IGNORECASE)
            branch = branch_match.group(1).strip() if branch_match else None
            
            # Extract commit message
            message_match = re.search(r'(?:commit\s+message)[:\s*`]+([^\n]+)', report_text, re.IGNORECASE)
            commit_message = message_match.group(1).strip() if message_match else None
            
            repo_path = os.getenv('TEST_ENV_PATH', '/unknown')
            repo_name = os.path.basename(repo_path)
            
            workflow = create_workflow_run(
                commit_id=commit_id,
                repo_path=repo_path,
                repo_name=repo_name,
                branch=branch,
                committer_name=committer_name,
                committer_email=committer_email,
                commit_message=commit_message
            )
            
            # Store IDs in state
            state["workflow_run_id"] = workflow.id
            state["commit_id"] = commit_id
            state["repo_path"] = repo_path
            
            print(f"✓ Workflow run created in database (ID: {workflow.id})")
            print(f"✓ State updated: workflow_run_id={workflow.id}, commit_id={commit_id}, repo_path={repo_path}\n")
            
        except Exception as e:
            print(f"⚠️  Warning: Failed to create workflow run in database: {e}\n")
            import traceback
            traceback.print_exc()
    
    return state