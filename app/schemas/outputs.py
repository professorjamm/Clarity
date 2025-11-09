"""
Output schemas for GH Triage Lite
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class FetchedItem(BaseModel):
    """Schema for fetched GitHub issues/PRs"""
    type: str = Field(..., description="'issue' or 'pr'")
    number: int = Field(..., description="Issue/PR number")
    title: str = Field(..., description="Title")
    body: Optional[str] = Field(None, description="Body content")
    labels: List[str] = Field(default_factory=list, description="Existing labels")
    state: str = Field(..., description="'open' or 'closed'")
    comments: int = Field(0, description="Number of comments")
    updated_at: str = Field(..., description="Last updated timestamp")
    html_url: str = Field(..., description="GitHub URL")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")


class Cluster(BaseModel):
    """Schema for issue clusters"""
    id: str = Field(..., description="Cluster ID")
    title: str = Field(..., description="Cluster title")
    summary: str = Field(..., description="3-5 line summary")
    members: List[int] = Field(default_factory=list, description="Issue/PR numbers")
    proposed_labels: List[str] = Field(default_factory=list, description="Suggested labels")
    uncertainty: float = Field(0.0, ge=0.0, le=1.0, description="Uncertainty score")


class PriorityEntry(BaseModel):
    """Schema for prioritized issues"""
    number: int = Field(..., description="Issue/PR number")
    title: str = Field(..., description="Issue title")
    severity: int = Field(..., ge=1, le=5, description="Severity score")
    impact: int = Field(..., ge=1, le=5, description="Impact score")
    effort: int = Field(..., ge=1, le=5, description="Effort score")
    score: float = Field(..., ge=0, le=100, description="Final priority score")
    justification: str = Field(..., description="Reasoning")
    links: List[str] = Field(default_factory=list, description="GitHub URLs")


class FixPlan(BaseModel):
    """Schema for fix plans"""
    number: int = Field(..., description="Issue/PR number")
    title: str = Field(..., description="Issue title")
    plan: List[str] = Field(default_factory=list, description="Step-by-step plan")
    files_likely_touched: List[str] = Field(default_factory=list, description="Files to modify")
    edge_cases: List[str] = Field(default_factory=list, description="Edge cases to consider")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria")
    test_hints: List[str] = Field(default_factory=list, description="Testing suggestions")
    citations: List[str] = Field(default_factory=list, description="GitHub URLs")


class CodePatch(BaseModel):
    """Schema for generated code patches"""
    issue_number: int = Field(..., description="Issue/PR number")
    file_path: str = Field(..., description="File path to patch")
    pseudocode: str = Field(..., description="Pseudocode with comments explaining the fix")
    explanation: str = Field(..., description="What the patch does")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    approach: Optional[str] = Field(None, description="Fix approach/strategy")
    notes: Optional[str] = Field(None, description="Additional notes or caveats")
    full_code: Optional[str] = Field(None, description="Optional full AI-generated code implementation")
    
    # Keep patch_content for backwards compatibility, but it will be the same as pseudocode
    @property
    def patch_content(self) -> str:
        """Backwards compatibility - returns pseudocode"""
        return self.pseudocode


class TriageResponse(BaseModel):
    """Final output schema for /triage endpoint"""
    repo: str = Field(..., description="Repository processed")
    generated_at: str = Field(..., description="Generation timestamp")
    clusters: List[Cluster] = Field(default_factory=list, description="Issue clusters")
    top_issues: List[PriorityEntry] = Field(default_factory=list, description="Top 3 issues")
    plans: List[FixPlan] = Field(default_factory=list, description="Fix plans for top issues")
    code_patches: List[CodePatch] = Field(default_factory=list, description="Generated code patches")
    report_markdown: str = Field(..., description="Formatted Markdown report")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata")

