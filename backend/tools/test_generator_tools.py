"""
Test Generator Tools for AgentOps.

Provides tools for test history exploration and test execution.
"""

from typing import Dict, Any, List, Optional
import subprocess
import json
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DEFAULT_REPO_PATH = os.getenv("TEST_ENV_PATH")


def explore_test_history(
    db_path: str = None
) -> Dict[str, Any]:
    """
    Provides database schema and connection info for agent to query test history.
    
    Agent can execute custom SQL queries to explore:
    - Previous test runs
    - Failure patterns
    - Coverage history
    - Flaky tests
    
    Args:
        db_path: Path to AgentOps database (defaults to backend/database/agentops.db)
    
    Returns:
        Dictionary with schema info, connection string, and example queries
    """
    import sqlite3
    import sys
    
    # Get default database path from connection module
    if db_path is None:
        backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        from database.connection import get_db_path
        db_path = get_db_path()
    
    # Ensure absolute path
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)
    
    # Check if database exists
    if not os.path.exists(db_path):
        return {
            'error': f'Database file not found at: {db_path}',
            'database_path': db_path,
            'suggestion': 'Please ensure the database has been initialized'
        }
    
    # Connect to database to get schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Get schema for each table
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = []
        for row in cursor.fetchall():
            columns.append({
                'name': row[1],
                'type': row[2],
                'nullable': not row[3],
                'primary_key': bool(row[5])
            })
        schema[table] = columns
    
    conn.close()
    
    return {
        'database_path': db_path,
        'connection_string': f'sqlite:///{db_path}',
        'tables': tables,
        'schema': schema,
        'example_queries': [
            {
                'description': 'Get recent test failures for a specific file',
                'query': "SELECT test_name, error_message, stack_trace, last_seen_at FROM test_failures WHERE source_file = ? AND resolved = 0 ORDER BY last_seen_at DESC LIMIT 5",
                'params': ['app.py']
            },
            {
                'description': 'Find flaky tests (failed multiple times)',
                'query': "SELECT test_name, occurrence_count, first_seen_at, last_seen_at FROM test_failures WHERE occurrence_count > 2 AND resolved = 0 ORDER BY occurrence_count DESC",
                'params': []
            },
            {
                'description': 'Get test coverage history for a file',
                'query': "SELECT tc.file_path, tc.coverage_percentage, te.started_at FROM test_coverage tc JOIN test_executions te ON tc.execution_id = te.execution_id WHERE tc.file_path = ? ORDER BY te.started_at DESC LIMIT 10",
                'params': ['app.py']
            },
            {
                'description': 'Get all test results for a specific commit',
                'query': "SELECT test_name, test_type, status, duration_seconds, error_message FROM test_results WHERE commit_id = ? AND repo_path = ?",
                'params': ['commit_hash', '/path/to/repo']
            },
            {
                'description': 'Find tests that consistently pass',
                'query': "SELECT test_name, COUNT(*) as run_count FROM test_results WHERE status = 'passed' GROUP BY test_name HAVING run_count > 5",
                'params': []
            }
        ],
        'usage_instructions': """
To query test history:
1. Use sqlite3 or SQLAlchemy to connect to the database
2. Execute SQL queries to explore test history
3. Use the schema information to understand table structure
4. Use example queries as templates for your own queries

Example Python code:
import sqlite3
conn = sqlite3.connect(database_path)
cursor = conn.cursor()
cursor.execute("SELECT * FROM test_failures WHERE source_file = ?", ["app.py"])
results = cursor.fetchall()
conn.close()
"""
    }


def execute_tests(
    test_code: str = None,
    test_type: str = "api",
    source_file: str = None,
    test_description: str = None,
    repo_path: str = DEFAULT_REPO_PATH,
    commit_id: str = None,
    store_results: bool = True,
    capture_coverage: bool = True,
    db_path: str = None
) -> Dict[str, Any]:
    """
    Execute tests using pytest and store results in database.
    
    Accepts test code directly, writes to temp file in /tmp (NOT in repo),
    executes tests, stores code and results in DB, then cleans up temp file.
    
    Steps:
    1. Write test code to temp file in /tmp (repo stays untouched)
    2. Store test code in database (test_scripts table)
    3. Run pytest with coverage
    4. Parse results (JUnit XML + coverage JSON)
    5. Store results in database (test_executions, test_results, test_coverage)
    6. Delete temp file
    7. Return results
    
    Args:
        test_code: Test code as string (REQUIRED)
        test_type: Type of test ('unit', 'api', 'database', 'validation', etc.)
        source_file: Source file being tested (e.g., 'server/app.py')
        test_description: Human-readable description of what test does
        repo_path: Path to repository (for pytest working directory)
        commit_id: Git commit ID (for database storage)
        store_results: Whether to store results in database
        capture_coverage: Whether to capture coverage metrics
        db_path: Path to AgentOps database
    
    Returns:
        Dictionary with test execution results
    """
    import sys
    
    if not test_code:
        return {
            'execution_id': f"exec_{uuid.uuid4().hex[:12]}",
            'status': 'error',
            'error': 'test_code parameter is required',
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0
        }
    
    # Get default database path from connection module
    if db_path is None or db_path == "database/agentops.db":
        backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        from database.connection import get_db_path
        db_path = get_db_path()
    
    # Check if coverage package is installed
    try:
        import coverage
    except ImportError:
        print("\n⚠️  WARNING: 'coverage' package not found")
        print("Installing coverage package...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "coverage"],
                capture_output=True,
                text=True,
                timeout=60
            )
            print("✓ Coverage package installed successfully")
        except Exception as e:
            print(f"✗ Failed to install coverage: {e}")
            print("Proceeding without coverage capture...")
            capture_coverage = False
    
    # Generate unique execution ID
    execution_id = f"exec_{uuid.uuid4().hex[:12]}"
    
    # Create temp file in /tmp (NOT in repo - repo stays untouched!)
    temp_file = f"/tmp/test_{execution_id}.py"
    temp_file_created = False
    
    try:
        with open(temp_file, 'w') as f:
            f.write(test_code)
        temp_file_created = True
        print(f"✓ Test code written to temp file: {temp_file}")
    except Exception as e:
        return {
            'execution_id': execution_id,
            'status': 'error',
            'error': f'Failed to write test file: {e}',
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0
        }
    
    # Store test code in database BEFORE execution
    if store_results and commit_id:
        try:
            backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)
            from database.operations import save_test_script
            
            # Count test functions in code
            test_count = test_code.count('def test_')
            
            save_test_script(
                commit_id=commit_id,
                repo_path=repo_path,
                test_file_path=None,  # No file path - it's temporary!
                source_file_path=source_file or "unknown",
                test_type=test_type,
                test_code=test_code,
                test_count=test_count,
                model_used="gemini-2.5-flash",
                prompt_used=test_description
            )
            print(f"✓ Test code stored in database")
        except Exception as e:
            print(f"⚠️  Warning: Failed to store test code in database: {e}")
    
    # Generate unique execution ID
    
    # Prepare pytest command
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        temp_file,  # Use temp file path
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        f"--junitxml=/tmp/{execution_id}_results.xml",  # JUnit XML output
    ]
    
    if capture_coverage:
        pytest_cmd.extend([
            "--cov=.",  # Coverage for current directory
            f"--cov-report=json:/tmp/{execution_id}_coverage.json",  # JSON coverage report
            "--cov-report=term",  # Terminal coverage report
        ])
    
    print(f"\n{'='*60}")
    print(f"Executing tests: {execution_id}")
    print(f"{'='*60}\n")
    print(f"Command: {' '.join(pytest_cmd)}")
    print(f"Working directory: {repo_path}\n")
    
    # Execute pytest
    started_at = datetime.utcnow()
    
    try:
        result = subprocess.run(
            pytest_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        completed_at = datetime.utcnow()
        duration = (completed_at - started_at).total_seconds()
        
        # Parse JUnit XML results
        test_results = _parse_junit_xml(f"/tmp/{execution_id}_results.xml")
        
        # Parse coverage JSON
        coverage_data = None
        if capture_coverage and os.path.exists(f"/tmp/{execution_id}_coverage.json"):
            coverage_data = _parse_coverage_json(f"/tmp/{execution_id}_coverage.json")
        
        # Prepare results
        execution_results = {
            'execution_id': execution_id,
            'started_at': started_at.isoformat(),
            'completed_at': completed_at.isoformat(),
            'duration_seconds': duration,
            'total_tests': test_results['total'],
            'passed': test_results['passed'],
            'failed': test_results['failed'],
            'skipped': test_results['skipped'],
            'errors': test_results['errors'],
            'status': 'completed' if result.returncode == 0 else 'failed',
            'coverage_percentage': coverage_data['summary']['percent_covered'] if coverage_data else None,
            'test_cases': test_results['test_cases'],
            'coverage_by_file': coverage_data['files'] if coverage_data else {},
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }
        
        # Store results in database
        if store_results and commit_id:
            try:
                _store_test_results(
                    execution_id=execution_id,
                    commit_id=commit_id,
                    repo_path=repo_path,
                    results=execution_results,
                    db_path=db_path
                )
                print(f"\n✓ Results stored in database")
            except Exception as db_error:
                print(f"\n⚠️  Warning: Failed to store results in database: {db_error}")
                print("Test execution completed successfully, but results were not stored.")
                execution_results['database_storage_error'] = str(db_error)
        
        print(f"\n{'='*60}")
        print(f"Test Execution Complete")
        print(f"{'='*60}")
        print(f"Total: {test_results['total']}")
        print(f"Passed: {test_results['passed']}")
        print(f"Failed: {test_results['failed']}")
        print(f"Skipped: {test_results['skipped']}")
        print(f"Duration: {duration:.2f}s")
        if coverage_data:
            print(f"Coverage: {coverage_data['summary']['percent_covered']:.1f}%")
        print(f"{'='*60}\n")
        
        # Clean up temp file (repo stays untouched!)
        if temp_file_created:
            try:
                os.remove(temp_file)
                print(f"✓ Temp file cleaned up: {temp_file}")
            except Exception as e:
                print(f"⚠️  Warning: Failed to delete temp file: {e}")
        
        return execution_results
        
    except subprocess.TimeoutExpired:
        # Clean up temp file even on timeout
        if temp_file_created:
            try:
                os.remove(temp_file)
            except:
                pass
        
        return {
            'execution_id': execution_id,
            'status': 'timeout',
            'error': 'Test execution timed out after 5 minutes',
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0
        }
    
    except Exception as e:
        # Clean up temp file even on error
        if temp_file_created:
            try:
                os.remove(temp_file)
            except:
                pass
        
        return {
            'execution_id': execution_id,
            'status': 'error',
            'error': str(e),
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0
        }


def _parse_junit_xml(xml_path: str) -> Dict[str, Any]:
    """Parse JUnit XML test results."""
    import xml.etree.ElementTree as ET
    
    if not os.path.exists(xml_path):
        return {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'test_cases': []
        }
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Get test suite stats
    testsuite = root if root.tag == 'testsuite' else root.find('testsuite')
    
    total = int(testsuite.get('tests', 0))
    failures = int(testsuite.get('failures', 0))
    errors = int(testsuite.get('errors', 0))
    skipped = int(testsuite.get('skipped', 0))
    passed = total - failures - errors - skipped
    
    # Parse individual test cases
    test_cases = []
    for testcase in testsuite.findall('testcase'):
        test_name = testcase.get('name')
        test_file = testcase.get('file', '')
        duration = float(testcase.get('time', 0))
        
        # Determine status
        failure = testcase.find('failure')
        error = testcase.find('error')
        skip = testcase.find('skipped')
        
        if failure is not None:
            status = 'failed'
            error_message = failure.get('message', '')
            stack_trace = failure.text or ''
        elif error is not None:
            status = 'error'
            error_message = error.get('message', '')
            stack_trace = error.text or ''
        elif skip is not None:
            status = 'skipped'
            error_message = skip.get('message', '')
            stack_trace = ''
        else:
            status = 'passed'
            error_message = ''
            stack_trace = ''
        
        test_cases.append({
            'test_name': test_name,
            'test_file': test_file,
            'status': status,
            'duration_seconds': duration,
            'error_message': error_message,
            'stack_trace': stack_trace
        })
    
    return {
        'total': total,
        'passed': passed,
        'failed': failures,
        'skipped': skipped,
        'errors': errors,
        'test_cases': test_cases
    }


def _parse_coverage_json(json_path: str) -> Dict[str, Any]:
    """Parse coverage JSON report."""
    if not os.path.exists(json_path):
        return None
    
    with open(json_path, 'r') as f:
        coverage_data = json.load(f)
    
    # Extract summary
    totals = coverage_data.get('totals', {})
    
    # Extract per-file coverage
    files = {}
    for file_path, file_data in coverage_data.get('files', {}).items():
        summary = file_data.get('summary', {})
        files[file_path] = {
            'lines_total': summary.get('num_statements', 0),
            'lines_covered': summary.get('covered_lines', 0),
            'lines_missed': summary.get('missing_lines', 0),
            'coverage_percentage': summary.get('percent_covered', 0)
        }
    
    return {
        'summary': {
            'lines_total': totals.get('num_statements', 0),
            'lines_covered': totals.get('covered_lines', 0),
            'percent_covered': totals.get('percent_covered', 0)
        },
        'files': files
    }


def _store_test_results(
    execution_id: str,
    commit_id: str,
    repo_path: str,
    results: Dict[str, Any],
    db_path: str
):
    """Store test results in database."""
    import sys
    import os
    
    # Add backend to path for imports
    backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    from database.operations import (
        create_test_execution,
        update_test_execution,
        save_test_result
    )
    
    # Create test execution record
    create_test_execution(
        execution_id=execution_id,
        commit_id=commit_id,
        repo_path=repo_path
    )
    
    # Update with results
    update_test_execution(
        execution_id=execution_id,
        total_tests=results['total_tests'],
        passed=results['passed'],
        failed=results['failed'],
        skipped=results['skipped'],
        errors=results.get('errors', 0),
        coverage_percentage=results.get('coverage_percentage'),
        duration_seconds=results['duration_seconds'],
        status=results['status']
    )
    
    # Save individual test results
    for test_case in results.get('test_cases', []):
        save_test_result(
            execution_id=execution_id,
            commit_id=commit_id,
            repo_path=repo_path,
            test_file=test_case['test_file'],
            test_name=test_case['test_name'],
            status=test_case['status'],
            duration_seconds=test_case['duration_seconds'],
            error_message=test_case.get('error_message'),
            stack_trace=test_case.get('stack_trace')
        )
