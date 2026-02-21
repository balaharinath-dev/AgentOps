from typing import List, Optional
from dotenv import load_dotenv

import subprocess
import os
import ast
import re

load_dotenv()

DEFAULT_REPO_PATH = os.getenv("TEST_ENV_PATH")

def execute_git_commands(
    commands: List[List[str]],
    repo_path: Optional[str] = DEFAULT_REPO_PATH
):
    """
    Execute multiple git commands inside a repository.
    
    This tool allows you to run any git commands to analyze the repository.
    Commands are executed sequentially in the specified repository path.

    :param commands: List of git command arrays.
                     Example: [["git", "pull"], ["git", "status"], ["git", "log", "-1"]]
                     
                     Common useful commands for analysis:
                     - ["git", "pull"] - Update repository
                     - ["git", "branch", "--show-current"] - Get current branch
                     - ["git", "log", "-1", "--pretty=format:%h|%an|%ad|%s"] - Latest commit details
                     - ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD"] - Files changed
                     - ["git", "diff", "--stat", "HEAD~1", "HEAD"] - Diff statistics
                     - ["git", "log", "-5", "--oneline"] - Recent commits
                     - ["git", "show", "HEAD", "--stat"] - Latest commit with stats
                     
    :param repo_path: Path to the repository (default is DEFAULT_REPO_PATH from .env)
    :return: List of results with stdout, stderr, and returncode for each command
    """

    results = []
    
    print(f"\n{'='*60}")
    print(f"Executing {len(commands)} git command(s) in: {repo_path}")
    print(f"{'='*60}\n")

    for idx, cmd in enumerate(commands, 1):
        cmd_str = ' '.join(cmd)
        print(f"[{idx}/{len(commands)}] Running: {cmd_str}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout for safety
            )

            status = "✓ SUCCESS" if result.returncode == 0 else "✗ FAILED"
            print(f"          Status: {status}")
            
            if result.stdout.strip():
                print(f"          Output: {result.stdout.strip()[:100]}...")
            if result.stderr.strip() and result.returncode != 0:
                print(f"          Error: {result.stderr.strip()[:100]}...")

            results.append({
                "command": cmd_str,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
                "success": result.returncode == 0
            })

        except subprocess.TimeoutExpired:
            print(f"          Status: ✗ TIMEOUT")
            results.append({
                "command": cmd_str,
                "stdout": "",
                "stderr": "Command timed out after 30 seconds",
                "returncode": -1,
                "success": False
            })
        except Exception as e:
            print(f"          Status: ✗ ERROR - {str(e)}")
            results.append({
                "command": cmd_str,
                "stdout": "",
                "stderr": f"Exception: {str(e)}",
                "returncode": -1,
                "success": False
            })
    
    print(f"\n{'='*60}")
    print(f"Completed: {sum(1 for r in results if r['success'])}/{len(results)} successful")
    print(f"{'='*60}\n")

    return results


def analyze_file_dependencies(
    changed_files: List[str],
    repo_path: Optional[str] = DEFAULT_REPO_PATH
) -> dict:
    """
    Analyze dependencies for changed files using AST parsing.
    Returns a simple list of files that depend on (import) the changed files.
    
    :param changed_files: List of changed file paths relative to repo
    :param repo_path: Path to the repository
    :return: Dictionary mapping changed files to their dependent files
    """
    
    if not repo_path or not os.path.exists(repo_path):
        return {"error": f"Repository path not found: {repo_path}"}
    
    print(f"\n{'='*60}")
    print(f"Analyzing dependencies for {len(changed_files)} file(s)")
    print(f"{'='*60}\n")
    
    dependencies = {}
    
    for changed_file in changed_files:
        changed_file = changed_file.strip()
        if not changed_file:
            continue
        
        file_ext = os.path.splitext(changed_file)[1]
        
        # Only analyze code files
        if file_ext not in ['.py', '.js', '.jsx', '.ts', '.tsx']:
            continue
        
        print(f"Checking: {changed_file}")
        
        # Find dependent files
        dependent_files = []
        
        if file_ext == '.py':
            dependent_files = _find_python_dependents(changed_file, repo_path)
        elif file_ext in ['.js', '.jsx', '.ts', '.tsx']:
            dependent_files = _find_js_dependents(changed_file, repo_path)
        
        dependencies[changed_file] = {
            "dependent_files": dependent_files,
            "count": len(dependent_files)
        }
        
        print(f"  → {len(dependent_files)} dependent file(s)\n")
    
    print(f"{'='*60}")
    print(f"Analysis complete")
    print(f"{'='*60}\n")
    
    return dependencies


def _find_python_dependents(target_file: str, repo_path: str) -> List[str]:
    """Find Python files that import the target file using AST."""
    
    dependents = []
    
    # Convert file path to module path
    module_path = target_file.replace('.py', '').replace('/', '.').replace('\\', '.')
    module_name = os.path.splitext(os.path.basename(target_file))[0]
    
    # Walk through Python files
    for root, _, files in os.walk(repo_path):
        if any(skip in root for skip in ['.git', '__pycache__', '.venv', 'venv', 'node_modules']):
            continue
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            
            if rel_path == target_file:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                # Check imports using AST
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if module_path in alias.name or module_name in alias.name:
                                dependents.append(rel_path)
                                break
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and (module_path in node.module or module_name in node.module):
                            dependents.append(rel_path)
                            break
            except:
                pass
    
    return list(set(dependents))


def _find_js_dependents(target_file: str, repo_path: str) -> List[str]:
    """Find JS/TS files that import the target file using regex."""
    
    dependents = []
    
    # Remove extension for import matching
    target_without_ext = os.path.splitext(target_file)[0]
    target_name = os.path.basename(target_without_ext)
    
    # Import patterns to search for
    import_patterns = [
        rf"from\s+['\"].*{re.escape(target_without_ext)}['\"]",
        rf"from\s+['\"].*{re.escape(target_name)}['\"]",
        rf"import\s+.*from\s+['\"].*{re.escape(target_without_ext)}['\"]",
        rf"require\(['\"].*{re.escape(target_without_ext)}['\"]\)",
    ]
    
    # Walk through JS/TS files
    for root, _, files in os.walk(repo_path):
        if any(skip in root for skip in ['.git', 'node_modules', 'dist', 'build', '.venv']):
            continue
        
        for file in files:
            if not any(file.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx']):
                continue
            
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            
            if rel_path == target_file:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if any import pattern matches
                for pattern in import_patterns:
                    if re.search(pattern, content):
                        dependents.append(rel_path)
                        break
            except:
                pass
    
    return list(set(dependents))