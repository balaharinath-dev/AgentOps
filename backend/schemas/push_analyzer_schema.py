"""
Output Schema for Push Analyzer Agent

Defines the expected structure of analysis output including dependency analysis.
"""

ANALYSIS_OUTPUT_SCHEMA = {
    "metadata": {
        "branch": "string",
        "commit_hash": "string",
        "author": "string",
        "timestamp": "string",
        "commit_message": "string"
    },
    "files_changed": {
        "total_files": "number",
        "lines_added": "number",
        "lines_deleted": "number",
        "by_status": {
            "modified": ["list of files"],
            "added": ["list of files"],
            "deleted": ["list of files"]
        },
        "by_category": {
            "backend": ["list of files"],
            "frontend": ["list of files"],
            "tests": ["list of files"],
            "config": ["list of files"],
            "docs": ["list of files"]
        }
    },
    "change_summary": {
        "description": "string - what changed",
        "affected_areas": ["list of modules/components"],
        "dependency_changes": ["list of dependency changes"],
        "new_files_count": "number",
        "modified_files_count": "number",
        "deleted_files_count": "number"
    },
    "dependency_analysis": {
        "changed_file_path": {
            "dependent_files": ["list of files that import this file"],
            "count": "number of dependent files"
        }
    },
    "impact_analysis": {
        "critical": ["list of critical changes"],
        "high": ["list of high priority changes (includes widely-used files)"],
        "medium": ["list of medium priority changes"],
        "low": ["list of low priority changes (isolated files)"],
        "breaking_changes": ["list of breaking changes"],
        "affected_modules": ["list of affected modules"]
    },
    "analysis_summary": {
        "key_findings": ["list of key findings"],
        "concerns": ["list of concerns or issues"],
        "focus_areas": ["areas requiring attention"],
        "risk_notes": "notes about files with many dependents"
    }
}

# Template for markdown output
OUTPUT_TEMPLATE = """
## 1. METADATA
- Branch: {branch}
- Commit: {commit_hash}
- Author: {author}
- Time: {timestamp}
- Message: {commit_message}

## 2. FILES CHANGED
Total: {total_files} files (+{lines_added} -{lines_deleted} lines)

By Status:
- Modified: {modified_count}
- Added: {added_count}
- Deleted: {deleted_count}

By Category:
- Backend: {backend_files}
- Frontend: {frontend_files}
- Tests: {test_files}
- Config: {config_files}
- Docs: {doc_files}

## 3. CHANGE SUMMARY
{change_description}

Affected Areas:
{affected_areas}

Dependency Changes:
{dependency_changes}

## 4. DEPENDENCY ANALYSIS

Changed Files & Dependencies:
{dependency_details}

Files with Most Dependents:
{top_dependent_files}

## 5. IMPACT ANALYSIS
CRITICAL:
{critical_items}

HIGH:
{high_items}

MEDIUM:
{medium_items}

LOW:
{low_items}

## 6. ANALYSIS SUMMARY
Key Findings:
{key_findings}

Concerns:
{concerns}

Focus Areas:
{focus_areas}

Risk Notes: {risk_notes}
"""