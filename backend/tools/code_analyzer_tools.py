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

from tree_sitter import Parser
from tree_sitter_typescript import language_tsx

JSX_EVENTS = {
    "onClick", "onChange", "onSubmit",
    "onKeyDown", "onKeyUp", "onBlur",
    "onFocus", "onMouseEnter", "onMouseLeave"
}

API_IDENTIFIERS = {"fetch", "axios"}

class ReactAnalyzer:
    def __init__(self, source_code: str):
        self.code = source_code.encode("utf-8")
        self.parser = Parser()
        self.parser.set_language(language_tsx())
        self.tree = self.parser.parse(self.code)
        self.root = self.tree.root_node

        self.result = {
            "component_name": None,
            "export_type": None,
            "props": [],
            "hooks": [],
            "state_variables": [],
            "custom_hooks": [],
            "event_handlers": [],
            "api_calls": [],
            "conditional_rendering": False,
            "forms_present": False
        }

    def analyze(self):
        self._walk(self.root)
        return self.result

    def _get_text(self, node):
        return self.code[node.start_byte:node.end_byte].decode("utf-8")

    def _walk(self, node):
        node_type = node.type

        # Component detection
        if node_type == "function_declaration":
            name = node.child_by_field_name("name")
            if name:
                self.result["component_name"] = self._get_text(name)

        # Arrow function component
        if node_type == "variable_declarator":
            name = node.child_by_field_name("name")
            value = node.child_by_field_name("value")
            if name and value and value.type == "arrow_function":
                self.result["component_name"] = self._get_text(name)

        # Export detection
        if node_type == "export_statement":
            self.result["export_type"] = "named"
        if node_type == "export_default_declaration":
            self.result["export_type"] = "default"

        # Hook detection
        if node_type == "call_expression":
            fn = node.child_by_field_name("function")
            if fn:
                fn_name = self._get_text(fn)
                if fn_name.startswith("use"):
                    if fn_name in ["useState", "useEffect", "useReducer", "useMemo", "useCallback"]:
                        self.result["hooks"].append(fn_name)
                    else:
                        self.result["custom_hooks"].append(fn_name)

                if fn_name in API_IDENTIFIERS:
                    self.result["api_calls"].append(fn_name)

        # State variable extraction
        if node_type == "variable_declarator":
            name = node.child_by_field_name("name")
            value = node.child_by_field_name("value")
            if value and value.type == "call_expression":
                fn = value.child_by_field_name("function")
                if fn and self._get_text(fn) == "useState":
                    if name:
                        self.result["state_variables"].append(self._get_text(name))

        # Conditional rendering detection
        if node_type in ["if_statement", "conditional_expression"]:
            self.result["conditional_rendering"] = True

        # JSX events
        if node_type == "jsx_attribute":
            attr_name = node.child_by_field_name("name")
            if attr_name:
                attr_text = self._get_text(attr_name)
                if attr_text in JSX_EVENTS:
                    self.result["event_handlers"].append(attr_text)

        # Form detection
        if node_type == "jsx_opening_element":
            tag = node.child_by_field_name("name")
            if tag:
                tag_name = self._get_text(tag)
                if tag_name in ["form", "input", "button", "select", "textarea"]:
                    self.result["forms_present"] = True

        for child in node.children:
            self._walk(child)


def analyze_react_file(file_path: str, repo_path: Optional[str] = DEFAULT_REPO_PATH):
    """
    Analyze a single React/TypeScript file using tree-sitter AST parsing.
    
    Extracts component structure, hooks, state, event handlers, and API calls.
    Supports .tsx, .ts, .jsx, and .js files.
    
    :param file_path: Relative path to the file from repo root (e.g., "src/App.tsx")
    :param repo_path: Path to the repository root [already set to default]
    :return: Dictionary with component analysis including hooks, state, events, etc.
    """
    full_path = os.path.join(repo_path, file_path) if repo_path else file_path
    
    with open(full_path, "r", encoding="utf-8") as f:
        code = f.read()

    analyzer = ReactAnalyzer(code)
    return analyzer.analyze()

def analyze_frontend_project(changed_files: List[str], repo_path: Optional[str] = DEFAULT_REPO_PATH):
    """
    Analyze multiple frontend files in a project.
    
    Processes all React/TypeScript files and returns detailed analysis for each.
    Filters for .tsx, .ts, .jsx, and .js files automatically.
    
    :param changed_files: List of relative file paths from repo root
    :param repo_path: Path to the repository root [already set to default]
    :return: Dictionary mapping file paths to their analysis results
    """
    results = {}
    for file in changed_files:
        if file.endswith((".tsx", ".ts", ".jsx", ".js")):
            try:
                results[file] = analyze_react_file(file, repo_path)
            except Exception as e:
                results[file] = {"error": str(e)}
    return results