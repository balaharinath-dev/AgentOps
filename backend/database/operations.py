"""
Common database operations for AgentOps.

Provides helper functions for CRUD operations on the database.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .models import (
    WorkflowRun, AgentState, TestScript, TestExecution,
    TestResult, TestFailure, TestCoverage
)
from .connection import get_session


def create_workflow_run(
    commit_id: str,
    repo_path: str,
    repo_name: str,
    branch: str = None
) -> WorkflowRun:
    """
    Create a new workflow run.
    
    Args:
        commit_id: Git commit ID
        repo_path: Path to repository
        repo_name: Name of repository
        branch: Git branch name
    
    Returns:
        WorkflowRun: Created workflow run instance
    """
    with get_session() as session:
        workflow = WorkflowRun(
            commit_id=commit_id,
            repo_path=repo_path,
            repo_name=repo_name,
            branch=branch,
            status='running'
        )
        session.add(workflow)
        session.commit()
        session.refresh(workflow)
        return workflow


def update_workflow_status(
    commit_id: str,
    repo_path: str,
    status: str,
    duration_seconds: float = None
) -> bool:
    """
    Update workflow run status.
    
    Args:
        commit_id: Git commit ID
        repo_path: Path to repository
        status: New status ('running', 'completed', 'failed', 'cancelled')
        duration_seconds: Total duration in seconds
    
    Returns:
        bool: True if successful
    """
    with get_session() as session:
        workflow = session.query(WorkflowRun).filter_by(
            commit_id=commit_id,
            repo_path=repo_path
        ).first()
        
        if workflow:
            workflow.status = status
            workflow.completed_at = datetime.utcnow()
            if duration_seconds:
                workflow.total_duration_seconds = duration_seconds
            session.commit()
            return True
        return False


def save_agent_state(
    commit_id: str,
    repo_path: str,
    agent_name: str,
    agent_output: List[Dict[str, Any]]
) -> AgentState:
    """
    Save or update agent state.
    
    Args:
        commit_id: Git commit ID
        repo_path: Path to repository
        agent_name: Name of agent ('orchestrator_agent', 'push_analyzer_agent', etc.)
        agent_output: List of agent output dictionaries
    
    Returns:
        AgentState: Updated agent state instance
    """
    with get_session() as session:
        # Try to get existing state
        state = session.query(AgentState).filter_by(
            commit_id=commit_id,
            repo_path=repo_path
        ).first()
        
        # Create new state if doesn't exist
        if not state:
            state = AgentState(
                commit_id=commit_id,
                repo_path=repo_path
            )
            session.add(state)
        
        # Update the specific agent's output
        setattr(state, agent_name, json.dumps(agent_output))
        state.updated_at = datetime.utcnow()
        
        session.commit()
        session.refresh(state)
        return state


def get_agent_state(
    commit_id: str,
    repo_path: str
) -> Optional[Dict[str, Any]]:
    """
    Get agent state for a commit.
    
    Args:
        commit_id: Git commit ID
        repo_path: Path to repository
    
    Returns:
        Dict with agent outputs or None if not found
    """
    with get_session() as session:
        state = session.query(AgentState).filter_by(
            commit_id=commit_id,
            repo_path=repo_path
        ).first()
        
        if not state:
            return None
        
        return {
            'orchestrator_agent': json.loads(state.orchestrator_agent) if state.orchestrator_agent else None,
            'push_analyzer_agent': json.loads(state.push_analyzer_agent) if state.push_analyzer_agent else None,
            'code_analyzer_agent': json.loads(state.code_analyzer_agent) if state.code_analyzer_agent else None,
            'test_generator_agent': json.loads(state.test_generator_agent) if state.test_generator_agent else None,
            'deployment_gateway_agent': json.loads(state.deployment_gateway_agent) if state.deployment_gateway_agent else None,
        }


def save_test_script(
    commit_id: str,
    repo_path: str,
    test_file_path: str,
    source_file_path: str,
    test_type: str,
    test_code: str,
    test_count: int = 0,
    model_used: str = None,
    prompt_used: str = None
) -> TestScript:
    """
    Save generated test script.
    
    Args:
        commit_id: Git commit ID
        repo_path: Path to repository
        test_file_path: Path to test file
        source_file_path: Path to source file being tested
        test_type: Type of test
        test_code: Full test code
        test_count: Number of test functions
        model_used: LLM model used
        prompt_used: Prompt used to generate test
    
    Returns:
        TestScript: Created test script instance
    """
    with get_session() as session:
        test_script = TestScript(
            commit_id=commit_id,
            repo_path=repo_path,
            test_file_path=test_file_path,
            source_file_path=source_file_path,
            test_type=test_type,
            test_code=test_code,
            test_count=test_count,
            model_used=model_used,
            prompt_used=prompt_used
        )
        session.add(test_script)
        session.commit()
        session.refresh(test_script)
        return test_script


def create_test_execution(
    execution_id: str,
    commit_id: str,
    repo_path: str,
    python_version: str = None,
    pytest_version: str = None
) -> TestExecution:
    """
    Create a new test execution record.
    
    Args:
        execution_id: Unique execution ID
        commit_id: Git commit ID
        repo_path: Path to repository
        python_version: Python version
        pytest_version: Pytest version
    
    Returns:
        TestExecution: Created test execution instance
    """
    with get_session() as session:
        execution = TestExecution(
            execution_id=execution_id,
            commit_id=commit_id,
            repo_path=repo_path,
            python_version=python_version,
            pytest_version=pytest_version,
            status='running'
        )
        session.add(execution)
        session.commit()
        session.refresh(execution)
        return execution


def update_test_execution(
    execution_id: str,
    total_tests: int = None,
    passed: int = None,
    failed: int = None,
    skipped: int = None,
    errors: int = None,
    coverage_percentage: float = None,
    lines_covered: int = None,
    lines_total: int = None,
    duration_seconds: float = None,
    status: str = None
) -> bool:
    """
    Update test execution with results.
    
    Args:
        execution_id: Unique execution ID
        total_tests: Total number of tests
        passed: Number of passed tests
        failed: Number of failed tests
        skipped: Number of skipped tests
        errors: Number of errors
        coverage_percentage: Overall coverage percentage
        lines_covered: Number of lines covered
        lines_total: Total number of lines
        duration_seconds: Execution duration
        status: Execution status
    
    Returns:
        bool: True if successful
    """
    with get_session() as session:
        execution = session.query(TestExecution).filter_by(
            execution_id=execution_id
        ).first()
        
        if not execution:
            return False
        
        if total_tests is not None:
            execution.total_tests = total_tests
        if passed is not None:
            execution.passed = passed
        if failed is not None:
            execution.failed = failed
        if skipped is not None:
            execution.skipped = skipped
        if errors is not None:
            execution.errors = errors
        if coverage_percentage is not None:
            execution.coverage_percentage = coverage_percentage
        if lines_covered is not None:
            execution.lines_covered = lines_covered
        if lines_total is not None:
            execution.lines_total = lines_total
        if duration_seconds is not None:
            execution.duration_seconds = duration_seconds
        if status is not None:
            execution.status = status
            execution.completed_at = datetime.utcnow()
        
        session.commit()
        return True


def save_test_result(
    execution_id: str,
    commit_id: str,
    repo_path: str,
    test_file: str,
    test_name: str,
    status: str,
    test_type: str = None,
    test_class: str = None,
    source_file: str = None,
    duration_seconds: float = None,
    error_message: str = None,
    error_type: str = None,
    stack_trace: str = None,
    failure_line: int = None
) -> TestResult:
    """
    Save individual test result.
    
    Args:
        execution_id: Unique execution ID
        commit_id: Git commit ID
        repo_path: Path to repository
        test_file: Path to test file
        test_name: Name of test function
        status: Test status ('passed', 'failed', 'skipped', 'error')
        test_type: Type of test
        test_class: Test class name (if applicable)
        source_file: Source file being tested
        duration_seconds: Test duration
        error_message: Error message (if failed)
        error_type: Error type (if failed)
        stack_trace: Stack trace (if failed)
        failure_line: Line number where failure occurred
    
    Returns:
        TestResult: Created test result instance
    """
    with get_session() as session:
        result = TestResult(
            execution_id=execution_id,
            commit_id=commit_id,
            repo_path=repo_path,
            test_file=test_file,
            test_name=test_name,
            status=status,
            test_type=test_type,
            test_class=test_class,
            source_file=source_file,
            duration_seconds=duration_seconds,
            error_message=error_message,
            error_type=error_type,
            stack_trace=stack_trace,
            failure_line=failure_line
        )
        session.add(result)
        session.commit()
        session.refresh(result)
        return result


def query_test_history(
    source_file: str = None,
    test_name: str = None,
    status: str = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Query test history with filters.
    
    Args:
        source_file: Filter by source file
        test_name: Filter by test name
        status: Filter by status
        limit: Maximum number of results
    
    Returns:
        List of test result dictionaries
    """
    with get_session() as session:
        query = session.query(TestResult)
        
        if source_file:
            query = query.filter(TestResult.source_file == source_file)
        if test_name:
            query = query.filter(TestResult.test_name == test_name)
        if status:
            query = query.filter(TestResult.status == status)
        
        results = query.order_by(TestResult.created_at.desc()).limit(limit).all()
        
        return [
            {
                'test_name': r.test_name,
                'test_file': r.test_file,
                'source_file': r.source_file,
                'status': r.status,
                'duration_seconds': r.duration_seconds,
                'error_message': r.error_message,
                'commit_id': r.commit_id,
                'created_at': r.created_at.isoformat() if r.created_at else None
            }
            for r in results
        ]
