from collections.abc import Sequence
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, Security
from fastapi.security import OAuth2PasswordRequestForm, SecurityScopes
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app import models as m
from app import schemas as s
from app.config import get_settings
from app.database import Base
from app.security import (
    DB,
    DUMMY_HASH,
    authenticate,
    create_token,
    current_user,
    oauth2,
    password_hash,
    permissions_for,
)

router = APIRouter(prefix="/api")
Reader = Annotated[m.User, Security(current_user, scopes=["directory:read"])]
Writer = Annotated[m.User, Security(current_user, scopes=["records:write"])]
SecretWriter = Annotated[m.User, Security(current_user, scopes=["confidential:write"])]
PositiveId = Annotated[int, Path(gt=0, le=2147483647)]
Page = Annotated[int, Query(ge=1, le=100000)]
PageSize = Annotated[int, Query(ge=1, le=100)]


def get_record[Record: Base](db: Session, model: type[Record], record_id: int) -> Record:
    record = db.get(model, record_id)
    if record is None:
        raise HTTPException(404, "Record not found.")
    return record


def related_record[Record: m.Employment | m.ComplianceRecord](
    db: Session, model: type[Record], person_id: int, record_id: int
) -> Record:
    record = get_record(db, model, record_id)
    if record.person_id != person_id:
        raise HTTPException(404, "Record not found.")
    return record


def update_record[Record: Base](db: Session, record: Record, data: s.Input) -> Record:
    for field, value in data.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.post("/auth/token", response_model=s.TokenOut, tags=["Authentication"])
def login(db: DB, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> s.TokenOut:
    # Bound work before hashing; never echo submitted credentials in an error.
    if len(form.username) > 80 or len(form.password) > 1024:
        raise HTTPException(
            401, "Invalid username or password.", headers={"WWW-Authenticate": "Bearer"}
        )
    user = db.scalar(select(m.User).where(m.User.username == form.username))
    valid = password_hash.verify(form.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(
            401, "Invalid username or password.", headers={"WWW-Authenticate": "Bearer"}
        )
    return s.TokenOut(
        access_token=create_token(user), expires_in=get_settings().access_token_minutes * 60
    )


@router.get("/auth/me", response_model=s.UserOut, tags=["Authentication"])
def me(user: Annotated[m.User, Depends(current_user)]) -> s.UserOut:
    return s.UserOut(
        id=user.id,
        username=user.username,
        roles=sorted(role.name for role in user.roles),
        permissions=permissions_for(user),
    )


@router.get("/departments", response_model=list[str], tags=["Directory"])
def departments(db: DB, user: Reader) -> Sequence[str]:
    return db.scalars(select(m.Person.department).distinct().order_by(m.Person.department)).all()


@router.get("/people", response_model=s.PeoplePage, tags=["Directory"])
def people(
    db: DB,
    user: Reader,
    q: Annotated[str, Query(max_length=120)] = "",
    department: Annotated[str | None, Query(max_length=80)] = None,
    status: s.EmploymentStatus | None = None,
    classification_id: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
    page: Page = 1,
    page_size: PageSize = 12,
) -> s.PeoplePage:
    filters = []
    if q.strip():
        filters.append(m.Person.name.icontains(q.strip(), autoescape=True))
    if department:
        filters.append(m.Person.department == department)
    employment_filters = []
    if status:
        employment_filters.append(m.Employment.status == status)
    if classification_id:
        employment_filters.append(m.Employment.classification_id == classification_id)
    if employment_filters:
        filters.append(m.Person.employments.any(and_(*employment_filters)))
    total = db.execute(select(func.count()).select_from(m.Person).where(*filters)).scalar_one()
    items = db.scalars(
        select(m.Person)
        .where(*filters)
        .order_by(func.lower(m.Person.name), m.Person.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return s.PeoplePage(
        items=[s.PersonOut.model_validate(person) for person in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/people", response_model=s.PersonOut, status_code=201, tags=["Directory"])
def create_person(data: s.PersonCreate, db: DB, user: Writer) -> m.Person:
    person = m.Person(**data.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.get("/people/{person_id}", response_model=s.ProfileOut, tags=["Directory"])
def profile(person_id: PositiveId, db: DB, user: Reader) -> m.Person:
    person = db.scalar(
        select(m.Person)
        .where(m.Person.id == person_id)
        .options(selectinload(m.Person.employments), selectinload(m.Person.compliance_records))
    )
    if person is None:
        raise HTTPException(404, "Record not found.")
    return person


@router.put("/people/{person_id}", response_model=s.PersonOut, tags=["Directory"])
def update_person(person_id: PositiveId, data: s.PersonWrite, db: DB, user: Writer) -> m.Person:
    return update_record(db, get_record(db, m.Person, person_id), data)


@router.get("/classifications", response_model=list[s.ClassificationOut], tags=["Classifications"])
def classifications(db: DB, user: Reader) -> Sequence[m.Classification]:
    return db.scalars(select(m.Classification).order_by(m.Classification.name)).all()


@router.post(
    "/classifications",
    response_model=s.ClassificationOut,
    status_code=201,
    tags=["Classifications"],
)
def create_classification(data: s.ClassificationWrite, db: DB, user: Writer) -> m.Classification:
    record = m.Classification(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put(
    "/classifications/{classification_id}",
    response_model=s.ClassificationOut,
    tags=["Classifications"],
)
def update_classification(
    classification_id: PositiveId, data: s.ClassificationWrite, db: DB, user: Writer
) -> m.Classification:
    return update_record(db, get_record(db, m.Classification, classification_id), data)


@router.delete("/classifications/{classification_id}", status_code=204, tags=["Classifications"])
def delete_classification(classification_id: PositiveId, db: DB, user: Writer) -> None:
    db.delete(get_record(db, m.Classification, classification_id))
    db.commit()


@router.post(
    "/people/{person_id}/employments",
    response_model=s.EmploymentOut,
    status_code=201,
    tags=["Employment"],
)
def create_employment(
    person_id: PositiveId, data: s.EmploymentCreate, db: DB, user: Writer
) -> m.Employment:
    get_record(db, m.Person, person_id)
    get_record(db, m.Classification, data.classification_id)
    record = m.Employment(person_id=person_id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put(
    "/people/{person_id}/employments/{employment_id}",
    response_model=s.EmploymentOut,
    tags=["Employment"],
)
def update_employment(
    person_id: PositiveId, employment_id: PositiveId, data: s.EmploymentWrite, db: DB, user: Writer
) -> m.Employment:
    record = related_record(db, m.Employment, person_id, employment_id)
    get_record(db, m.Classification, data.classification_id)
    return update_record(db, record, data)


@router.delete(
    "/people/{person_id}/employments/{employment_id}", status_code=204, tags=["Employment"]
)
def delete_employment(
    person_id: PositiveId, employment_id: PositiveId, db: DB, user: Writer
) -> None:
    db.delete(related_record(db, m.Employment, person_id, employment_id))
    db.commit()


@router.post(
    "/people/{person_id}/compliance",
    response_model=s.ComplianceOut,
    status_code=201,
    tags=["Compliance"],
)
def create_compliance(
    person_id: PositiveId, data: s.ComplianceWrite, db: DB, user: Writer
) -> m.ComplianceRecord:
    get_record(db, m.Person, person_id)
    record = m.ComplianceRecord(person_id=person_id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put(
    "/people/{person_id}/compliance/{record_id}",
    response_model=s.ComplianceOut,
    tags=["Compliance"],
)
def update_compliance(
    person_id: PositiveId, record_id: PositiveId, data: s.ComplianceWrite, db: DB, user: Writer
) -> m.ComplianceRecord:
    return update_record(db, related_record(db, m.ComplianceRecord, person_id, record_id), data)


@router.delete("/people/{person_id}/compliance/{record_id}", status_code=204, tags=["Compliance"])
def delete_compliance(person_id: PositiveId, record_id: PositiveId, db: DB, user: Writer) -> None:
    db.delete(related_record(db, m.ComplianceRecord, person_id, record_id))
    db.commit()


CONFIDENTIAL_FIELDS = ["private_notes", "employments.salary"]


def log_access(
    db: Session,
    user: m.User,
    person_id: int,
    person: m.Person | None,
    outcome: Literal["success", "denied", "not_found"],
) -> None:
    db.add(
        m.AuditEvent(
            actor_id=user.id,
            target_person_id=person.id if person else None,
            requested_person_id=person_id,
            action="confidential.read",
            field_names=CONFIDENTIAL_FIELDS,
            outcome=outcome,
        )
    )
    # Deliberately synchronous and fail-closed: a failed commit must prevent disclosure.
    db.commit()


def confidential_reader(
    person_id: PositiveId,
    db: DB,
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2)],
) -> m.User:
    user = authenticate(db, token)
    permissions = permissions_for(user)
    if any(scope not in permissions for scope in security_scopes.scopes):
        person = db.get(m.Person, person_id)
        log_access(db, user, person_id, person, "denied")
        raise HTTPException(
            403, "Only HR can reveal confidential details. This attempt was audited."
        )
    return user


@router.get(
    "/people/{person_id}/confidential", response_model=s.ConfidentialOut, tags=["Confidential"]
)
def confidential(
    person_id: PositiveId,
    db: DB,
    user: Annotated[m.User, Security(confidential_reader, scopes=["confidential:read"])],
) -> s.ConfidentialOut:
    person = db.get(m.Person, person_id)
    if person is None:
        log_access(db, user, person_id, None, "not_found")
        raise HTTPException(404, "Record not found.")
    result = s.ConfidentialOut(
        person_id=person.id,
        private_notes=person.private_notes,
        employments=[
            s.ConfidentialEmployment(employment_id=e.id, job_title=e.job_title, salary=e.salary)
            for e in person.employments
        ],
    )
    log_access(db, user, person_id, person, "success")
    return result


@router.patch("/people/{person_id}/confidential", status_code=204, tags=["Confidential"])
def update_notes(person_id: PositiveId, data: s.NotesWrite, db: DB, user: SecretWriter) -> Response:
    update_record(db, get_record(db, m.Person, person_id), data)
    return Response(status_code=204)


@router.patch(
    "/people/{person_id}/employments/{employment_id}/salary", status_code=204, tags=["Confidential"]
)
def update_salary(
    person_id: PositiveId,
    employment_id: PositiveId,
    data: s.SalaryWrite,
    db: DB,
    user: SecretWriter,
) -> Response:
    update_record(db, related_record(db, m.Employment, person_id, employment_id), data)
    return Response(status_code=204)


@router.get("/audit", response_model=s.AuditPage, tags=["Audit"])
def audit(
    db: DB,
    user: Annotated[m.User, Security(current_user, scopes=["audit:read"])],
    page: Page = 1,
    page_size: PageSize = 20,
    person_id: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
) -> s.AuditPage:
    filters = [m.AuditEvent.requested_person_id == person_id] if person_id else []
    total = db.execute(select(func.count()).select_from(m.AuditEvent).where(*filters)).scalar_one()
    records = db.scalars(
        select(m.AuditEvent)
        .where(*filters)
        .order_by(m.AuditEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return s.AuditPage(
        items=[
            s.AuditOut(
                id=r.id,
                actor=r.actor.username,
                target_person_id=r.target_person_id,
                requested_person_id=r.requested_person_id,
                action=r.action,
                field_names=r.field_names,
                timestamp=r.timestamp,
                outcome=r.outcome,
            )
            for r in records
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
