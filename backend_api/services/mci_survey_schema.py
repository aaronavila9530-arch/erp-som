"""Web-only MCI survey contract; independent from desktop report columns."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SECTION_TITLES = {
    "instructions": "INSTRUCTIONS, SCOPE AND METHODOLOGY",
    "work": "Work performed",
    "limitations": "Main limitations of this report",
    "chronology": "Time and place of arrival and chronology of events",
    "representatives": "Representatives",
    "findings": "SURVEY FINDINGS",
    "visual": "Visual inspection",
    "provided": "Documentation provided",
    "missing": "Documentation not provided",
    "conclusion": "CONCLUSION",
    "enclosure": "ENCLOSURE",
}


class TextBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(default="", max_length=30000)


class OptionalSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    # Disabled text is retained for editing; exports must filter on enabled.
    blocks: list[TextBlock] = Field(default_factory=list, max_length=100)


class SurveyContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    imo: str = Field(default="", max_length=100)
    length_and_tonnage: str = Field(default="", max_length=1000)
    cargo: str = Field(default="", max_length=3000)
    period_start: datetime | None = None
    period_end: datetime | None = None
    issue_date: date | None = None
    report_status: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=300)
    location: str = Field(default="", max_length=500)
    master: str = Field(default="", max_length=200)
    chief_officer: str = Field(default="", max_length=200)
    surveyor: str = Field(default="", max_length=200)
    sections: dict[str, OptionalSection] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_content(self):
        if set(self.sections) - SECTION_TITLES.keys():
            raise ValueError("Unknown report section")
        if self.period_start and self.period_end:
            if (self.period_start.tzinfo is None) != (self.period_end.tzinfo is None):
                raise ValueError("Both period dates must use the same timezone convention")
            if self.period_end < self.period_start:
                raise ValueError("Inspection end precedes start")
        total = sum(len(block.text) for section in self.sections.values() for block in section.blocks)
        if total > 500000:
            raise ValueError("Report narrative exceeds supported size")
        strings = [v for v in self.model_dump().values() if isinstance(v, str)]
        strings.extend(block.text for section in self.sections.values() for block in section.blocks)
        if any("\x00" in value for value in strings):
            raise ValueError("Invalid control character")
        return self


class SurveySave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["vessel", "condition", "cargo"]
    service_id: int = Field(gt=0)
    content: SurveyContent
    version: str | None = None
    submit: bool = False
    # Company, report number, vessel and client are server-derived, not accepted.


def export_sections(content: SurveyContent):
    """Fixed template order, never request-dictionary order or stale disabled text."""
    return [(key, SECTION_TITLES[key], [block.text for block in content.sections[key].blocks
                                      if block.text.strip()])
            for key in SECTION_TITLES if key in content.sections and content.sections[key].enabled]
