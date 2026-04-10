from pydantic import BaseModel, Field
from typing import Dict, List


class ExperienceItem(BaseModel):
    company: str = ""
    location: str = ""
    title: str = ""
    dates: str = ""
    bullets: List[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str = ""
    description: List[str] = Field(default_factory=list)


class SectionItem(BaseModel):
    original_title: str = ""
    canonical_label: str = "Custom"
    content: List[str] = Field(default_factory=list)


class ResumeSchema(BaseModel):
    name: str = ""
    contact_info: List[str] = Field(default_factory=list)
    summary: str = ""
    skills: Dict[str, List[str]] = Field(default_factory=dict)
    languages: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    sections: List[SectionItem] = Field(default_factory=list)


class JDSchema(BaseModel):
    job_title: str = ""
    company: str = ""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class SkillMatch(BaseModel):
    skill: str
    matched: bool
    evidence: List[str] = Field(default_factory=list)
    gap_reason: str = ""


class AlignmentResult(BaseModel):
    matched_skills: List[SkillMatch] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    matched_responsibilities: List[str] = Field(default_factory=list)