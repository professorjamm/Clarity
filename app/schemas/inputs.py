"""
Input schemas for GH Triage Lite
"""
from pydantic import BaseModel, Field
from typing import Optional


class TriageRequest(BaseModel):
    """Request schema for /triage endpoint"""
    repo: str = Field(..., description="Repository in format 'owner/name'")
    limit: int = Field(50, ge=1, le=100, description="Max number of issues to fetch")
    include_prs: bool = Field(True, description="Include pull requests")
    include_issues: bool = Field(True, description="Include issues")
    language_hint: str = Field("auto", description="Programming language hint")

