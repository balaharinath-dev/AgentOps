import warnings
warnings.filterwarnings("ignore")

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from prompts.orchestrator_prompt import ORCHESTRATOR_SYSTEM_PROMPT as SYSTEM_PROMPT

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
)

def orchestrator_agent(state: GraphState):
    # Determine which agent just ran by checking state
    agent_outputs = {
        "push_analyzer": state.get("push_analyzer_agent", []),
        "code_analyzer": state.get("code_analyzer_agent", []),
        "test_generator": state.get("test_generator_agent", []),
    }
    
    # Find the most recently updated agent
    current_agent_name = None
    current_agent_output = None
    
    for agent_name, outputs in agent_outputs.items():
        if outputs:
            current_agent_name = agent_name
            current_agent_output = outputs[-1]
    
    # If no agent has run yet, default to push_analyzer (first agent)
    if not current_agent_name:
        current_agent_name = "push_analyzer"
        current_agent_output = "No output available - First run"
    
    # Gather all previous reports for context
    push_report = agent_outputs["push_analyzer"][-1] if agent_outputs["push_analyzer"] else "Not available"
    code_report = agent_outputs["code_analyzer"][-1] if agent_outputs["code_analyzer"] else "Not available"
    test_report = agent_outputs["test_generator"][-1] if agent_outputs["test_generator"] else "Not available"
    
    # Build dynamic initial query based on which agent just ran
    initial_query = f"""
    Review the output from the {current_agent_name.replace('_', ' ').title()} Agent and determine the next step.

    Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    Current Agent: {current_agent_name}

    CUMULATIVE REPORTS (for context):

    Push Analyzer Report:
    {push_report}

    Code Analyzer Report:
    {code_report}

    Test Generator Report:
    {test_report}

    Current Agent Output (focus validation here):
    {current_agent_output}

    Validate the current agent's output and decide:
    - If quality is good: Specify the next agent to proceed
    - If quality is inadequate: Request rework from {current_agent_name} with specific recommendations

    Provide your validation and decision.
    """

    response = agent.invoke({"messages": [{"role": "user", "content": initial_query}]})

    print("\n" + "="*80)
    print(" "*25 + "ORCHESTRATOR VALIDATION")
    print("="*80 + "\n")

    # Extract and print the validation
    validation_content = response.get("messages")[-1].content
    if isinstance(validation_content, list):
        # Handle list format from the response
        for content_block in validation_content:
            if isinstance(content_block, dict) and "text" in content_block:
                print(content_block["text"])
            else:
                print(content_block)
    else:
        # Handle string format
        print(validation_content)

    print("\n" + "="*80)
    print(" "*28 + "END OF VALIDATION")
    print("="*80 + "\n")

    state["orchestrator_agent"] = state.get("orchestrator_agent", [])
    state["orchestrator_agent"].append({"validation": validation_content})
    state["next_agent"] = validation_content

    return state