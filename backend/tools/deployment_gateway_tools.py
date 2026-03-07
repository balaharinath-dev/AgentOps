"""
Deployment Gateway Tools for AgentOps.

Provides tools for Jira integration and deployment decision making.
"""

import os
import json
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


def _get_jira_account_id_from_email(
    email: str, 
    jira_url: str, 
    auth: HTTPBasicAuth
) -> Optional[str]:
    """
    Get Jira account ID from email address.
    
    Args:
        email: Email address to search for
        jira_url: Jira instance URL
        auth: HTTPBasicAuth object
    
    Returns:
        Account ID if found, None otherwise
    """
    try:
        headers = {"Accept": "application/json"}
        
        # Search for user by email
        response = requests.get(
            f"{jira_url}/rest/api/3/user/search",
            params={"query": email},
            headers=headers,
            auth=auth,
            timeout=10
        )
        
        if response.status_code == 200:
            users = response.json()
            if users and len(users) > 0:
                # Return the first matching user's account ID
                return users[0].get('accountId')
        
        return None
    
    except Exception:
        return None


def create_jira_story_with_tasks(
    commit_id: str,
    repo_path: str,
    project_key: str,
    summary: str,
    description_text: str,
    assignee_email: Optional[str] = None,
    tasks: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Create a Jira Story with optional child tasks for deployment blocking issues.
    
    This tool is used when deployment is BLOCKED due to test failures or quality issues.
    It creates a Jira story assigned to the committer with detailed failure information.
    
    Args:
        commit_id: Git commit ID that triggered the issue
        repo_path: Path to repository
        project_key: Jira project key (e.g., "CICD", "AGENTOPS")
        summary: Story title (e.g., "Deployment Blocked: Test Failures in commit abc123")
        description_text: Story description with failure details
        assignee_email: Email address of committer to assign the story to
        tasks: List of task summaries to create under the story (e.g., ["Fix test_login_failure", "Fix test_api_validation"])
    
    Returns:
        Dictionary with story_key, story_url, tasks, and success status
    """
    JIRA_URL = os.getenv("JIRA_URL")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_TOKEN = os.getenv("JIRA_TOKEN")
    
    if not all([JIRA_URL, JIRA_EMAIL, JIRA_TOKEN]):
        return {
            "error": "Jira credentials not configured. Set JIRA_URL, JIRA_EMAIL, and JIRA_TOKEN in .env",
            "success": False
        }
    
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    # Look up assignee account ID from email
    assignee_account_id = None
    if assignee_email:
        assignee_account_id = _get_jira_account_id_from_email(assignee_email, JIRA_URL, auth)
        if not assignee_account_id:
            print(f"⚠️  Warning: Could not find Jira user with email {assignee_email}")
    
    # Jira description format (ADF - Atlassian Document Format)
    description = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": description_text}
                ],
            }
        ],
    }
    
    # Create Story
    story_payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Story"},
            "labels": ["agentops", "deployment-blocked", f"commit-{commit_id[:8]}"]
        }
    }
    
    if assignee_account_id:
        story_payload["fields"]["assignee"] = {"accountId": assignee_account_id}
    
    print(f"\n{'='*60}")
    print(f"Creating Jira Story")
    print(f"{'='*60}\n")
    print(f"Project: {project_key}")
    print(f"Summary: {summary}")
    print(f"Assignee: {assignee_email or 'Unassigned'}")
    
    try:
        response = requests.post(
            f"{JIRA_URL}/rest/api/3/issue",
            headers=headers,
            auth=auth,
            data=json.dumps(story_payload),
            timeout=30
        )
        response.raise_for_status()
        
        story_data = response.json()
        story_key = story_data["key"]
        story_url = f"{JIRA_URL}/browse/{story_key}"
        
        print(f"✓ Story created: {story_key}")
        print(f"  URL: {story_url}\n")
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to create Jira story: {str(e)}"
        print(f"✗ {error_msg}\n")
        return {
            "error": error_msg,
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
            "success": False
        }
    
    # Create Tasks
    created_tasks = []
    if tasks:
        print(f"Creating {len(tasks)} task(s)...")
        for idx, task_summary in enumerate(tasks, 1):
            task_payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": task_summary,
                    "issuetype": {"name": "Task"},
                    "parent": {"key": story_key},
                }
            }
            
            try:
                r = requests.post(
                    f"{JIRA_URL}/rest/api/3/issue",
                    headers=headers,
                    auth=auth,
                    data=json.dumps(task_payload),
                    timeout=30
                )
                r.raise_for_status()
                
                task_data = r.json()
                task_key = task_data["key"]
                task_url = f"{JIRA_URL}/browse/{task_key}"
                
                created_tasks.append({
                    "key": task_key,
                    "url": task_url,
                    "summary": task_summary
                })
                
                print(f"  [{idx}/{len(tasks)}] ✓ Task created: {task_key}")
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to create task '{task_summary}': {str(e)}"
                print(f"  [{idx}/{len(tasks)}] ✗ {error_msg}")
                created_tasks.append({
                    "error": error_msg,
                    "summary": task_summary
                })
    
    print(f"\n{'='*60}")
    print(f"Jira Story Creation Complete")
    print(f"{'='*60}\n")
    
    return {
        "story_key": story_key,
        "story_url": story_url,
        "tasks": created_tasks,
        "commit_id": commit_id,
        "repo_path": repo_path,
        "success": True
    }


def store_deployment_decision(
    workflow_run_id: str,
    commit_id: str,
    repo_path: str,
    deployment_status: str,
    jira_story_key: Optional[str] = None,
    jira_story_url: Optional[str] = None,
    jira_task_keys: Optional[str] = None
) -> Dict[str, Any]:
    """
    Store deployment decision and Jira ticket information in the database.
    
    This tool stores the final deployment decision (DEPLOY or BLOCK) along with
    any associated Jira tickets in the database for tracking and reporting.
    
    Args:
        workflow_run_id: Database workflow_run.id (UUID string)
        commit_id: Git commit ID
        repo_path: Path to repository
        deployment_status: "DEPLOY" or "BLOCK"
        jira_story_key: Jira story key (e.g., "CICD-123") - required if BLOCK
        jira_story_url: Full URL to the Jira story - required if BLOCK
        jira_task_keys: Comma-separated list of task keys (optional)
    
    Returns:
        Dictionary with success status and message
    """
    import sys
    
    # Add backend to path for imports
    backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    from database.operations import update_workflow_deployment_decision
    
    try:
        result = update_workflow_deployment_decision(
            commit_id=commit_id,
            repo_path=repo_path,
            deployment_status=deployment_status,
            jira_story_key=jira_story_key,
            jira_story_url=jira_story_url,
            jira_task_keys=jira_task_keys
        )
        
        if result:
            print(f"✓ Deployment decision stored in database")
            print(f"  Workflow Run ID: {workflow_run_id}")
            print(f"  Status: {deployment_status}")
            if jira_story_key:
                print(f"  Jira Story: {jira_story_key}")
            
            return {
                "success": True,
                "message": "Deployment decision stored successfully",
                "workflow_run_id": workflow_run_id,
                "deployment_status": deployment_status,
                "jira_story_key": jira_story_key
            }
        else:
            print(f"✗ Failed to store deployment decision - workflow run not found")
            return {
                "success": False,
                "message": "Failed to store deployment decision - workflow run not found"
            }
    
    except Exception as e:
        error_msg = f"Failed to store deployment decision: {str(e)}"
        print(f"✗ {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": error_msg,
            "error": str(e)
        }
