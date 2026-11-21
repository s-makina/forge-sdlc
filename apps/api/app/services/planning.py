"""Feature-planning pipeline service (Phase 5.3, G2).

Turns a feature request into a plan: testable requirements + acceptance
criteria (business analyst), a module breakdown/plan summary (architect), and
an ordered set of ``Task`` records with dependencies (project manager). This is
the testable control-plane model of the planning agents; the orchestrator
worker mirrors it in Temporal (README §10, FR-6.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.workflow_instance import Workflow
from app.schemas.tasks import TaskCreate
from app.services import tasks as task_service


@dataclass
class PlanResult:
    """Outcome of decomposing a feature request into a plan."""

    requirements: list[str] = field(default_factory=list)
    plan_summary: str = ""
    tasks: list[Task] = field(default_factory=list)


def plan_from_feature(db: Session, workflow: Workflow) -> PlanResult:
    """Decompose a feature workflow's inputs into requirements + tasks.

    The feature description drives the decomposition deterministically so the
    pipeline is testable without a live model. Requirements and the plan summary
    are recorded back onto the workflow; concrete tasks are created with explicit
    dependency edges for scheduling (README §11).
    """
    inputs = workflow.inputs or {}
    title = str(inputs.get("title") or workflow.name or "Untitled feature")
    description = str(inputs.get("description") or "")
    repo_url = str(inputs["repository_url"]) if inputs.get("repository_url") else None

    requirements = _derive_requirements(title, description)
    plan_summary = _plan_summary(title, requirements)
    tasks = _create_tasks(db, workflow, title, requirements, repo_url)

    # Record the requirements + plan summary on the workflow durably.
    workflow.inputs = {
        **dict(inputs),
        "requirements": requirements,
        "plan_summary": plan_summary,
    }
    db.commit()

    return PlanResult(
        requirements=requirements,
        plan_summary=plan_summary,
        tasks=tasks,
    )


def _derive_requirements(title: str, description: str) -> list[str]:
    """Turn a feature request into testable requirements + acceptance criteria."""
    core = description.strip() or f"the {title.strip().lower()} capability"
    return [
        f"As an operator I can use {core} so the platform behaves as specified. "
        "Acceptance: the feature is present and usable without error.",
        f"As a user I understand {title.strip().lower()} from the product surface. "
        "Acceptance: the change is documented and the expected inputs/outputs are clear.",
        f"As an operator I can verify {title.strip().lower()} in an isolated workspace. "
        "Acceptance: tests pass and no unrelated code is changed.",
    ]


def _plan_summary(title: str, requirements: list[str]) -> str:
    """Produce a short plan summary for the operator's approval review."""
    return (
        f"Plan for '{title}': {len(requirements)} testable requirements; "
        "implement the feature in a dedicated branch, cover it with tests, "
        "and route it through code review before delivery."
    )


def _create_tasks(
    db: Session,
    workflow: Workflow,
    title: str,
    requirements: list[str],
    repo_url: str | None,
) -> list[Task]:
    """Create the task records for the plan, chaining their dependencies."""
    subject = title.strip().lower()
    acceptance = "\n".join(requirements)

    specs = [
        (
            "Write requirements & acceptance criteria",
            "documentation",
            "business_analyst",
            acceptance,
        ),
        (
            "Design architecture & module boundaries",
            "documentation",
            "software_architect",
            "Define the modules, API contracts and data ownership for the feature.",
        ),
        (
            f"Implement {subject}",
            "feature",
            "software_engineer",
            f"The feature works as specified: {acceptance}",
        ),
        (
            f"Write tests for {subject}",
            "testing",
            "qa_engineer",
            "Tests cover the changed behaviour and its boundaries; they pass.",
        ),
        (
            f"Review {subject}",
            "testing",
            "code_reviewer",
            "Independent review finds no blocking defects; findings are actionable.",
        ),
    ]

    created: list[Task] = []
    for task_title, task_type, role, criteria in specs:
        deps = [created[-1].id] if created else []
        task = task_service.create_task(
            db,
            TaskCreate(
                project_id=workflow.project_id,
                workflow_id=workflow.id,
                title=task_title,
                task_type=task_type,  # type: ignore[arg-type]
                assigned_role=role,
                acceptance_criteria=criteria,
                repository_url=repo_url,
                target_branch="main",
                skills=[_skill_for_role(role)],
                dependencies=deps,
            ),
        )
        created.append(task)
    return created


def _skill_for_role(role: str) -> str:
    """Best-effort skill hint per planning role (matches seeded skills)."""
    return {
        "business_analyst": "requirements-analysis",
        "software_architect": "architecture-design",
        "project_manager": "task-planning",
        "software_engineer": "clean-code",
        "qa_engineer": "software-testing",
        "code_reviewer": "code-review",
    }.get(role, "clean-code")
