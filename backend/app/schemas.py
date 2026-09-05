from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Name = Annotated[str, Field(min_length=1, max_length=120)]
Department = Annotated[str, Field(min_length=1, max_length=80)]
Salary = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
EmploymentStatus = Literal["active", "on_leave", "ended"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PersonWrite(Input):
    name: Name
    work_email: Annotated[EmailStr, Field(max_length=254)]
    department: Department

    @field_validator("work_email")
    @classmethod
    def lower_email(cls, value: str) -> str:
        return value.lower()


class PersonCreate(PersonWrite):
    private_notes: str = Field(default="", max_length=5000)


class PersonOut(Output):
    id: int
    name: str
    work_email: str
    department: str


class ClassificationWrite(Input):
    name: Annotated[str, Field(min_length=1, max_length=80)]

    @field_validator("name")
    @classmethod
    def lower_name(cls, value: str) -> str:
        return value.lower()


class ClassificationOut(Output):
    id: int
    name: str


class EmploymentWrite(Input):
    job_title: Name
    start_date: date
    end_date: date | None = None
    status: EmploymentStatus
    classification_id: int = Field(gt=0, le=2147483647)

    @model_validator(mode="after")
    def dates(self) -> Self:
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self


class EmploymentCreate(EmploymentWrite):
    salary: Salary


class EmploymentOut(Output):
    id: int
    person_id: int
    job_title: str
    start_date: date
    end_date: date | None
    status: str
    classification: ClassificationOut


class ComplianceWrite(Input):
    requirement: Annotated[str, Field(min_length=1, max_length=160)]
    status: Literal["pending", "completed"]
    completion_date: date | None = None
    expiry_date: date | None = None

    @model_validator(mode="after")
    def dates(self) -> Self:
        if self.status == "completed" and not self.completion_date:
            raise ValueError("Completed training requires a completion date")
        if self.status == "pending" and (self.completion_date or self.expiry_date):
            raise ValueError("Pending training cannot have completion or expiry dates")
        if self.expiry_date and self.completion_date and self.expiry_date < self.completion_date:
            raise ValueError("Expiry must be on or after completion")
        return self


class ComplianceOut(Output):
    id: int
    person_id: int
    requirement: str
    status: str
    completion_date: date | None
    expiry_date: date | None


class ProfileOut(PersonOut):
    employments: list[EmploymentOut]
    compliance_records: list[ComplianceOut]


class PeoplePage(BaseModel):
    items: list[PersonOut]
    total: int
    page: int
    page_size: int


class NotesWrite(Input):
    private_notes: str = Field(max_length=5000)


class SalaryWrite(Input):
    salary: Salary


class ConfidentialEmployment(BaseModel):
    employment_id: int
    job_title: str
    salary: Decimal


class ConfidentialOut(BaseModel):
    person_id: int
    private_notes: str
    employments: list[ConfidentialEmployment]


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    permissions: list[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuditOut(BaseModel):
    id: int
    actor: str
    target_person_id: int | None
    requested_person_id: int
    action: str
    field_names: list[str]
    timestamp: datetime
    outcome: str


class AuditPage(BaseModel):
    items: list[AuditOut]
    total: int
    page: int
    page_size: int
