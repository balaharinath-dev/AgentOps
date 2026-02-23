from typing import List, Optional, Dict, Any
from collections import defaultdict
from dotenv import load_dotenv

import subprocess
import os

import ast

load_dotenv()

DEFAULT_REPO_PATH = os.getenv("TEST_ENV_PATH")

def execute_cli_commands(
    commands: List[List[str]],
    working_dir: Optional[str] = DEFAULT_REPO_PATH,
    use_sudo: bool = False,
    sudo_password: Optional[str] = "bala@user",
    timeout: int = 30,
    env: Optional[Dict[str, str]] = None
):
    """
    Execute multiple CLI commands sequentially.

    :param commands: List of command arrays.
                     Example:
                     [
                        ["ls", "-la"],
                        ["systemctl", "status", "nginx"]
                     ]

    :param working_dir: Directory to execute commands in [already set to default].
    :param use_sudo: Whether to prepend sudo to commands.
    :param sudo_password: Optional sudo password (only if required) [already set to default password].
                          NOTE: Avoid using password in production — prefer NOPASSWD sudo.
    :param timeout: Timeout per command in seconds.
    :param env: Optional environment variables.
    :return: List of result dictionaries.
    """

    results = []

    print(f"\n{'='*60}")
    print(f"Executing {len(commands)} CLI command(s)")
    print(f"{'='*60}\n")

    for idx, cmd in enumerate(commands, 1):

        # Add sudo if required
        if use_sudo:
            cmd = ["sudo", "-S"] + cmd

        cmd_str = " ".join(cmd)
        print(f"[{idx}/{len(commands)}] Running: {cmd_str}")

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                input=(sudo_password + "\n") if (use_sudo and sudo_password) else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, **env} if env else None
            )

            status = "✓ SUCCESS" if result.returncode == 0 else "✗ FAILED"
            print(f"          Status: {status}")

            if result.stdout.strip():
                print(f"          Output: {result.stdout.strip()[:200]}")

            if result.stderr.strip() and result.returncode != 0:
                print(f"          Error: {result.stderr.strip()[:200]}")

            results.append({
                "command": cmd_str,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
                "success": result.returncode == 0
            })

        except subprocess.TimeoutExpired:
            print("          Status: ✗ TIMEOUT")
            results.append({
                "command": cmd_str,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
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

def analyze_python_ast(repo_path: str) -> Dict[str, Any]:
    """
    Analyze Python files in a repository using AST parsing.
    
    Extracts classes, functions, and imports from all Python files.
    Returns a detailed report with file-level and aggregate statistics.
    
    :param repo_path: Path to the repository to analyze
    :return: Dictionary with files list and total counts
    """
    report = {
        "files": [],
        "total_classes": 0,
        "total_functions": 0,
        "total_imports": 0
    }

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)

                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                file_data = {
                    "file": file_path,
                    "classes": [],
                    "functions": [],
                    "imports": []
                }

                for node in ast.walk(tree):

                    if isinstance(node, ast.ClassDef):
                        file_data["classes"].append({
                            "name": node.name,
                            "bases": [base.id for base in node.bases if isinstance(base, ast.Name)]
                        })
                        report["total_classes"] += 1

                    if isinstance(node, ast.FunctionDef):
                        file_data["functions"].append({
                            "name": node.name,
                            "args": len(node.args.args),
                            "lineno": node.lineno
                        })
                        report["total_functions"] += 1

                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            file_data["imports"].append(alias.name)
                            report["total_imports"] += 1

                report["files"].append(file_data)

    return report

def build_dependency_graph(ast_report: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Build an internal dependency graph from AST analysis report.
    
    Creates a mapping of files to their imported modules.
    Useful for understanding code coupling and dependencies.
    
    :param ast_report: AST report from analyze_python_ast function
    :return: Dictionary mapping file names to sets of imported modules
    """
    graph = defaultdict(set)

    for file_data in ast_report["files"]:
        file_name = file_data["file"]
        for imp in file_data["imports"]:
            graph[file_name].add(imp)

    # Convert sets to lists for JSON serialization
    return {k: list(v) for k, v in graph.items()}

def detect_cycles(graph: Dict[str, List[str]]) -> bool:
    """
    Detect circular dependencies in a dependency graph.
    
    Uses depth-first search to identify cycles in the import graph.
    Returns True if any circular dependencies are found.
    
    :param graph: Dependency graph from build_dependency_graph function
    :return: Boolean indicating whether cycles exist
    """
    visited = set()
    stack = set()

    def dfs(node):
        if node in stack:
            return True
        if node in visited:
            return False

        visited.add(node)
        stack.add(node)

        for neighbor in graph.get(node, []):
            if dfs(neighbor):
                return True

        stack.remove(node)
        return False

    return any(dfs(node) for node in graph)

def compute_metrics(ast_report: Dict[str, Any]) -> Dict[str, List[Any]]:
    """
    Compute code quality metrics from AST analysis report.
    
    Identifies large classes and complex functions based on thresholds.
    Large classes have >10 classes, complex functions have >5 parameters.
    
    :param ast_report: AST report from analyze_python_ast function
    :return: Dictionary with lists of large classes and complex functions
    """
    large_classes = []
    long_functions = []

    for file in ast_report["files"]:
        if len(file["classes"]) > 10:
            large_classes.append(file["file"])

        for func in file["functions"]:
            if func["args"] > 5:
                long_functions.append((file["file"], func["name"]))

    return {
        "large_classes": large_classes,
        "complex_functions": long_functions
    }