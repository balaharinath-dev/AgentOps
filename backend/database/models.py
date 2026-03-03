"""
SQLAlchemy models for AgentOps database.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKeyConstraint, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class WorkflowRun(Base):
    """Track each workflow execution (one per commit)"""
    __tablename__ = 'workflow_runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    commit_id = Column(String(255), nullable=False)
    repo_path = Column(String(500), nullable=False)
    repo_name = Column(String(255), nullable=False)
    branch = Column(String(255))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(50), default='running')
    total_duration_seconds = Column(Float)
    
    __table_args__ = (
        UniqueConstraint('commit_id', 'repo_path', name='uq_workflow_commit_repo'),
        CheckConstraint("status IN ('running', 'completed', 'failed', 'cancelled')", name='ck_workflow_status'),
        Index('idx_workflow_commit_repo', 'commit_id', 'repo_path'),
        Index('idx_workflow_status', 'status'),
        Index('idx_workflow_started', 'started_at'),
    )
    
    def __repr__(self):
        return f"<WorkflowRun(commit_id='{self.commit_id}', repo_name='{self.repo_name}', status='{self.status}')>"


class AgentState(Base):
    """Store state for all agents"""
    __tablename__ = 'agent_states'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    commit_id = Column(String(255), nullable=False)
    repo_path = Column(String(500), nullable=False)
    
    # Agent outputs stored as JSON strings
    orchestrator_agent = Column(Text)  # JSON: List[Dict[str, Any]]
    push_analyzer_agent = Column(Text)  # JSON: List[Dict[str, Any]]
    code_analyzer_agent = Column(Text)  # JSON: List[Dict[str, Any]]
    test_generator_agent = Column(Text)  # JSON: List[Dict[str, Any]]
    deployment_gateway_agent = Column(Text)  # JSON: List[Dict[str, Any]]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['commit_id', 'repo_path'],
            ['workflow_runs.commit_id', 'workflow_runs.repo_path'],
            name='fk_agent_states_workflow'
        ),
        UniqueConstraint('commit_id', 'repo_path', name='uq_agent_states_commit_repo'),
        Index('idx_agent_states_commit_repo', 'commit_id', 'repo_path'),
    )
    
    def __repr__(self):
        return f"<AgentState(commit_id='{self.commit_id}', repo_path='{self.repo_path}')>"



class TestScript(Base):
    """Store all generated test code"""
    __tablename__ = 'test_scripts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    commit_id = Column(String(255), nullable=False)
    repo_path = Column(String(500), nullable=False)
    
    # Test file information
    test_file_path = Column(String(500), nullable=False)
    source_file_path = Column(String(500), nullable=False)
    test_type = Column(String(50), nullable=False)
    
    # Test code
    test_code = Column(Text, nullable=False)
    test_count = Column(Integer, default=0)
    
    # Metadata
    generated_by = Column(String(100), default='test_generator_agent')
    generated_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String(100))
    prompt_used = Column(Text)
    
    # Execution tracking
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime)
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['commit_id', 'repo_path'],
            ['workflow_runs.commit_id', 'workflow_runs.repo_path'],
            name='fk_test_scripts_workflow'
        ),
        UniqueConstraint('commit_id', 'repo_path', 'test_file_path', name='uq_test_scripts_commit_repo_file'),
        CheckConstraint(
            "test_type IN ('unit', 'api', 'database', 'auth', 'authorization', "
            "'validation', 'integration', 'e2e', 'security', 'dependency', "
            "'migration', 'health', 'logging')",
            name='ck_test_scripts_type'
        ),
        Index('idx_test_scripts_commit_repo', 'commit_id', 'repo_path'),
        Index('idx_test_scripts_source', 'source_file_path'),
        Index('idx_test_scripts_type', 'test_type'),
    )
    
    def __repr__(self):
        return f"<TestScript(test_file='{self.test_file_path}', type='{self.test_type}')>"


class TestExecution(Base):
    """Track each test execution run"""
    __tablename__ = 'test_executions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(255), unique=True, nullable=False)
    commit_id = Column(String(255), nullable=False)
    repo_path = Column(String(500), nullable=False)
    
    # Execution details
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    # Test statistics
    total_tests = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    
    # Coverage
    coverage_percentage = Column(Float)
    lines_covered = Column(Integer)
    lines_total = Column(Integer)
    
    # Status
    status = Column(String(50), default='running')
    
    # Environment
    python_version = Column(String(50))
    pytest_version = Column(String(50))
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['commit_id', 'repo_path'],
            ['workflow_runs.commit_id', 'workflow_runs.repo_path'],
            name='fk_test_executions_workflow'
        ),
        UniqueConstraint('commit_id', 'repo_path', name='uq_test_executions_commit_repo'),
        CheckConstraint("status IN ('running', 'completed', 'failed', 'cancelled')", name='ck_test_executions_status'),
        Index('idx_test_executions_commit_repo', 'commit_id', 'repo_path'),
        Index('idx_test_executions_status', 'status'),
        Index('idx_test_executions_started', 'started_at'),
    )
    
    def __repr__(self):
        return f"<TestExecution(execution_id='{self.execution_id}', status='{self.status}', passed={self.passed}/{self.total_tests})>"


class TestResult(Base):
    """Store individual test case results"""
    __tablename__ = 'test_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(255), nullable=False)
    commit_id = Column(String(255), nullable=False)
    repo_path = Column(String(500), nullable=False)
    
    # Test identification
    test_file = Column(String(500), nullable=False)
    test_name = Column(String(255), nullable=False)
    test_class = Column(String(255))
    test_type = Column(String(50))
    
    # Source file being tested
    source_file = Column(String(500))
    
    # Result
    status = Column(String(50), nullable=False)
    duration_seconds = Column(Float)
    
    # Failure details
    error_message = Column(Text)
    error_type = Column(String(255))
    stack_trace = Column(Text)
    failure_line = Column(Integer)
    
    # Assertions
    assertions_count = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['execution_id'],
            ['test_executions.execution_id'],
            name='fk_test_results_execution'
        ),
        ForeignKeyConstraint(
            ['commit_id', 'repo_path'],
            ['workflow_runs.commit_id', 'workflow_runs.repo_path'],
            name='fk_test_results_workflow'
        ),
        UniqueConstraint('execution_id', 'test_file', 'test_name', name='uq_test_results_execution_test'),
        CheckConstraint("status IN ('passed', 'failed', 'skipped', 'error')", name='ck_test_results_status'),
        CheckConstraint(
            "test_type IN ('unit', 'api', 'database', 'auth', 'authorization', "
            "'validation', 'integration', 'e2e', 'security', 'dependency', "
            "'migration', 'health', 'logging')",
            name='ck_test_results_type'
        ),
        Index('idx_test_results_execution', 'execution_id'),
        Index('idx_test_results_commit_repo', 'commit_id', 'repo_path'),
        Index('idx_test_results_status', 'status'),
        Index('idx_test_results_test_name', 'test_name'),
        Index('idx_test_results_source_file', 'source_file'),
    )
    
    def __repr__(self):
        return f"<TestResult(test_name='{self.test_name}', status='{self.status}')>"


class TestFailure(Base):
    """Track test failures over time for pattern analysis"""
    __tablename__ = 'test_failures'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    test_result_id = Column(Integer, nullable=False)
    execution_id = Column(String(255), nullable=False)
    commit_id = Column(String(255), nullable=False)
    repo_path = Column(String(500), nullable=False)
    
    # Test identification
    test_name = Column(String(255), nullable=False)
    test_file = Column(String(500), nullable=False)
    source_file = Column(String(500))
    
    # Failure details
    failure_type = Column(String(100))
    error_type = Column(String(255))
    error_message = Column(Text)
    expected_value = Column(Text)
    actual_value = Column(Text)
    failure_line = Column(Integer)
    stack_trace = Column(Text)
    
    # Tracking
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    occurrence_count = Column(Integer, default=1)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['test_result_id'],
            ['test_results.id'],
            name='fk_test_failures_result'
        ),
        ForeignKeyConstraint(
            ['execution_id'],
            ['test_executions.execution_id'],
            name='fk_test_failures_execution'
        ),
        ForeignKeyConstraint(
            ['commit_id', 'repo_path'],
            ['workflow_runs.commit_id', 'workflow_runs.repo_path'],
            name='fk_test_failures_workflow'
        ),
        Index('idx_test_failures_commit_repo', 'commit_id', 'repo_path'),
        Index('idx_test_failures_test_name', 'test_name'),
        Index('idx_test_failures_resolved', 'resolved'),
        Index('idx_test_failures_occurrence', 'occurrence_count'),
    )
    
    def __repr__(self):
        return f"<TestFailure(test_name='{self.test_name}', occurrences={self.occurrence_count}, resolved={self.resolved})>"


class TestCoverage(Base):
    """Store coverage details per file"""
    __tablename__ = 'test_coverage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(255), nullable=False)
    commit_id = Column(String(255), nullable=False)
    repo_path = Column(String(500), nullable=False)
    
    # File information
    file_path = Column(String(500), nullable=False)
    
    # Coverage metrics
    lines_total = Column(Integer)
    lines_covered = Column(Integer)
    lines_missed = Column(Integer)
    coverage_percentage = Column(Float)
    
    # Branch coverage
    branches_total = Column(Integer)
    branches_covered = Column(Integer)
    branches_missed = Column(Integer)
    branch_coverage_percentage = Column(Float)
    
    # Function coverage
    functions_total = Column(Integer)
    functions_covered = Column(Integer)
    functions_missed = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['execution_id'],
            ['test_executions.execution_id'],
            name='fk_test_coverage_execution'
        ),
        ForeignKeyConstraint(
            ['commit_id', 'repo_path'],
            ['workflow_runs.commit_id', 'workflow_runs.repo_path'],
            name='fk_test_coverage_workflow'
        ),
        UniqueConstraint('execution_id', 'file_path', name='uq_test_coverage_execution_file'),
        Index('idx_test_coverage_execution', 'execution_id'),
        Index('idx_test_coverage_commit_repo', 'commit_id', 'repo_path'),
        Index('idx_test_coverage_file', 'file_path'),
        Index('idx_test_coverage_percentage', 'coverage_percentage'),
    )
    
    def __repr__(self):
        return f"<TestCoverage(file='{self.file_path}', coverage={self.coverage_percentage}%)>"
