"""
Configuration for Push Analyzer Agent
"""

# File categorization patterns
FILE_CATEGORIES = {
    "backend": [
        "*.py", "*.java", "*.go", "*.rb", "*.php",
        "**/server/**", "**/backend/**", "**/api/**",
        "**/models/**", "**/controllers/**", "**/services/**"
    ],
    "frontend": [
        "*.tsx", "*.jsx", "*.vue", "*.html", "*.css", "*.scss",
        "**/client/**", "**/frontend/**", "**/components/**",
        "**/pages/**", "**/views/**"
    ],
    "tests": [
        "test_*.py", "*_test.py", "*.test.ts", "*.test.js",
        "*.spec.ts", "*.spec.js", "**/tests/**", "**/__tests__/**"
    ],
    "config": [
        "*.json", "*.yaml", "*.yml", "*.toml", "*.ini",
        "*.config.js", "*.config.ts", "package.json",
        "requirements.txt", "Pipfile", "pyproject.toml",
        ".env*", "Dockerfile", "docker-compose.yml"
    ],
    "docs": [
        "*.md", "*.rst", "*.txt", "**/docs/**", "README*"
    ]
}

# Priority assessment keywords
PRIORITY_KEYWORDS = {
    "critical": [
        "auth", "authentication", "security", "password", "token",
        "database", "migration", "schema", "sql",
        "payment", "transaction", "billing", "critical"
    ],
    "high": [
        "api", "endpoint", "route", "feature",
        "refactor", "middleware", "service"
    ],
    "medium": [
        "component", "ui", "interface", "util", "helper",
        "validation", "config", "settings"
    ],
    "low": [
        "doc", "comment", "format", "style", "readme",
        "typo", "whitespace", "lint"
    ]
}
