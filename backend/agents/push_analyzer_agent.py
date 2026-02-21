import warnings
warnings.filterwarnings("ignore")

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from prompts.push_analyzer_prompt import PUSH_ANALYZER_SYSTEM_PROMPT as SYSTEM_PROMPT
from tools.push_analyzer_tools import execute_git_commands, analyze_file_dependencies

from dotenv import load_dotenv
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

# Get current timestamp
from datetime import datetime
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

initial_query = f"""
Analyze the latest push to the repository.

Current Time: {current_time}
Repository: {os.getenv('TEST_ENV_PATH', 'Not specified')}

Perform your analysis following your workflow:
1. Start with git pull and gather commit information
2. Identify changed files
3. Analyze dependencies for the changed files
4. Generate comprehensive structured report

Proceed dynamically.
"""

response = agent.invoke({"messages": [{"role": "user", "content": initial_query}]})

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