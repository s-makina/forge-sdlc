"""Project and repository service operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project, Repository
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    RepositoryCreate,
    RepositoryUpdate,
)


def list_projects(db: Session, *, include_inactive: bool = False) -> list[Project]:
    stmt = select(Project).options(selectinload(Project.repositories))
    if not include_inactive:
        stmt = stmt.where(Project.is_active.is_(True))
    return list(db.scalars(stmt.order_by(Project.name)).all())


def get_project(db: Session, project_id: int) -> Project | None:
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.repositories))
    )
    return db.scalar(stmt)


def create_project(db: Session, payload: ProjectCreate) -> Project:
    project = Project(
        name=payload.name,
        description=payload.description,
        default_branch=payload.default_branch,
    )
    db.add(project)
    db.flush()
    for repo_payload in payload.repositories:
        db.add(
            Repository(
                project_id=project.id,
                url=repo_payload.url,
                default_branch=repo_payload.default_branch,
            )
        )
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, payload: ProjectUpdate) -> Project:
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def add_repository(db: Session, project: Project, payload: RepositoryCreate) -> Repository:
    repository = Repository(
        project_id=project.id,
        url=payload.url,
        default_branch=payload.default_branch,
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)
    return repository


def get_repository(db: Session, repository_id: int) -> Repository | None:
    return db.get(Repository, repository_id)


def update_repository(db: Session, repository: Repository, payload: RepositoryUpdate) -> Repository:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        setattr(repository, field, value)
    db.commit()
    db.refresh(repository)
    return repository


def detect_adapter(repository: Repository) -> str:
    """Placeholder for technology-adapter detection (implemented in Phase 2).

    Returns the adapter status used to populate ``Repository.adapter_status``.
    """
    return "pending"
