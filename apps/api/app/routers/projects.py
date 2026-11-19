"""Project and repository routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps.auth import require_user
from app.models.project import Project, Repository
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectList,
    ProjectRead,
    ProjectUpdate,
    RepositoryCreate,
    RepositoryRead,
    RepositoryUpdate,
)
from app.services import audit, projects

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_or_404(db: Session, project_id: int) -> Project:
    project = projects.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_repository_or_404(db: Session, repository_id: int) -> Repository:
    repository = projects.get_repository(db, repository_id)
    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repository


@router.get("", response_model=ProjectList)
def list_projects(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ProjectList:
    items = projects.list_projects(db, include_inactive=include_inactive)
    return ProjectList(items=[ProjectRead.model_validate(p) for p in items], total=len(items))


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ProjectRead:
    project = projects.create_project(db, payload)
    audit.record_audit(
        db,
        action="project.create",
        entity_type="project",
        entity_id=str(project.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Created project '{project.name}'",
    )
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ProjectRead:
    project = _get_project_or_404(db, project_id)
    return ProjectRead.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ProjectRead:
    project = _get_project_or_404(db, project_id)
    updated = projects.update_project(db, project, payload)
    audit.record_audit(
        db,
        action="project.update",
        entity_type="project",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Updated project '{updated.name}'",
    )
    return ProjectRead.model_validate(updated)


@router.post("/{project_id}/repositories", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
def add_repository(
    project_id: int,
    payload: RepositoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> RepositoryRead:
    project = _get_project_or_404(db, project_id)
    repository = projects.add_repository(db, project, payload)
    audit.record_audit(
        db,
        action="repository.add",
        entity_type="repository",
        entity_id=str(repository.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Added repository '{repository.url}' to project '{project.name}'",
    )
    return RepositoryRead.model_validate(repository)


@router.patch("/{project_id}/repositories/{repository_id}", response_model=RepositoryRead)
def update_repository(
    project_id: int,
    repository_id: int,
    payload: RepositoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> RepositoryRead:
    project = _get_project_or_404(db, project_id)
    repository = _get_repository_or_404(db, repository_id)
    updated = projects.update_repository(db, repository, payload)
    audit.record_audit(
        db,
        action="repository.update",
        entity_type="repository",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Updated repository '{updated.url}' of project '{project.name}'",
    )
    return RepositoryRead.model_validate(updated)
