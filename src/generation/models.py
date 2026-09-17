from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


ShortText = Annotated[str, Field(min_length=1, max_length=100)]
Bullet = Annotated[str, Field(min_length=1, max_length=220)]


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Language(ProfileModel):
    name: ShortText
    level: Literal["A1", "A2", "B1", "B2", "C1", "C2", "native"]


class Experience(ProfileModel):
    company: ShortText
    position: ShortText
    start_date: date = Field(description="First day of the start month.")
    end_date: date | None = Field(description="First day of the end month; null if current.")
    achievements: list[Bullet] = Field(min_length=1, max_length=3)
    technologies: list[ShortText] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def check_dates(self) -> Self:
        """Reject reversed employment dates and employment dates in the future."""
        if self.start_date > date.today():
            raise ValueError("Experience cannot start in the future.")
        if self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("Experience must end after it starts.")
            if self.end_date > date.today():
                raise ValueError("Completed experience cannot end in the future.")
        return self


class Education(ProfileModel):
    institution: ShortText
    qualification: ShortText
    field_of_study: ShortText
    start_year: int = Field(ge=1950, le=2100)
    end_year: int | None = Field(description="Graduation year; null if still studying.", ge=1950, le=2100)

    @model_validator(mode="after")
    def check_years(self) -> Self:
        """Check that education starts before graduation and neither is in the future."""
        if self.start_year > date.today().year:
            raise ValueError("Education cannot start in the future.")
        if self.end_year is not None:
            if not self.start_year <= self.end_year <= date.today().year:
                raise ValueError("Graduation year must be between start year and current year.")
        return self


class CandidateProfile(ProfileModel):
    first_name: ShortText
    last_name: ShortText
    position: ShortText
    seniority: Literal["intern", "junior", "middle", "senior", "lead"]
    location: ShortText
    email: ShortText = Field(description="Fictional email using example.com.")
    summary: str = Field(min_length=1, max_length=450)
    skills: list[ShortText] = Field(min_length=3, max_length=12)
    languages: list[Language] = Field(min_length=1, max_length=4)
    experience: list[Experience] = Field(min_length=1, max_length=3)
    education: list[Education] = Field(min_length=1, max_length=2)


class CandidateBrief(ProfileModel):
    """Compact planning data used to make one candidate distinct from another."""

    role: ShortText
    seniority: Literal["intern", "junior", "middle", "senior", "lead"]
    location: ShortText
    focus_areas: list[ShortText] = Field(min_length=2, max_length=5)
    languages: list[ShortText] = Field(min_length=1, max_length=3)
    career_angle: str = Field(min_length=1, max_length=220)


class CandidateBriefPlan(ProfileModel):
    """Validated collection of runtime-generated candidate briefs."""

    candidates: list[CandidateBrief] = Field(min_length=1, max_length=10)
