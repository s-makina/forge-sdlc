"""ORM models package. Import all models so Alembic autogenerate sees them."""

from app.models.agent import Agent, AgentSkill, AgentStatus, AgentToolPermission, AgentVersion
from app.models.approval import ApprovalStatus, PlanApproval
from app.models.audit import AuditLog
from app.models.model_provider import (
    CheckKind,
    Model,
    ModelProfile,
    ModelProvider,
    ProviderCheck,
    ProviderType,
    UsageRecord,
)
from app.models.project import Project, Repository
from app.models.registry import Skill, Tool
from app.models.task import Task, TaskDependency, TaskPriority, TaskStatus, TaskType
from app.models.user import User
from app.models.workflow import (
    WorkflowStage,
    WorkflowTemplate,
    WorkflowTemplateCategory,
)
from app.models.workflow_instance import Workflow, WorkflowStageRun, WorkflowStatus

__all__ = [
    "Agent",
    "AgentSkill",
    "AgentStatus",
    "AgentToolPermission",
    "AgentVersion",
    "ApprovalStatus",
    "AuditLog",
    "CheckKind",
    "Model",
    "ModelProfile",
    "ModelProvider",
    "PlanApproval",
    "Project",
    "ProviderCheck",
    "ProviderType",
    "Repository",
    "Skill",
    "Task",
    "TaskDependency",
    "TaskPriority",
    "TaskStatus",
    "TaskType",
    "Tool",
    "UsageRecord",
    "User",
    "Workflow",
    "WorkflowStage",
    "WorkflowStageRun",
    "WorkflowStatus",
    "WorkflowTemplate",
    "WorkflowTemplateCategory",
]
