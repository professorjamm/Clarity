"""
Orchestration Router - Coordinates all agents with ReAct pattern
"""
import time
from datetime import datetime
from typing import Tuple, List, Dict, Any
from app.schemas.inputs import TriageRequest
from app.schemas.outputs import TriageResponse, FetchedItem, CodePatch
from app.tools.github import GitHubClient
from app.llm import LLMClient, get_llm_client
from app.agents.summarizer import cluster_issues
from app.agents.labeler import label_clusters
from app.agents.prioritizer import prioritize_issues
from app.agents.fix_plan import generate_fix_plans
from app.agents.code_generator import generate_code_patch
from app.agents.editor import format_report
from app.llm import MODEL

# Global progress tracking
_progress_log: List[Dict[str, Any]] = []
_current_session_id: str = ""


def add_progress(message: str, emoji: str = "🔄"):
    """Add a progress message to the log"""
    global _progress_log
    _progress_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "message": message,
        "emoji": emoji
    })
    # Print to console as well
    print(f"{emoji} {message}")


def clear_progress(session_id: str):
    """Clear progress for a new session"""
    global _progress_log, _current_session_id
    _current_session_id = session_id
    _progress_log = []


def get_progress():
    """Get current progress log"""
    return {
        "session_id": _current_session_id,
        "log": _progress_log
    }


async def triage_repository(request: TriageRequest) -> TriageResponse:
    """
    Main orchestration function that runs the full multi-agent pipeline
    
    Pipeline:
    1. Fetch issues/PRs from GitHub
    2. Summarizer: Cluster issues (with ReAct)
    3. Labeler: Suggest labels (with ReAct)
    4. Prioritizer: Score and select Top 3
    5. Fix-Plan: Generate detailed plans for Top 3
    6. Editor: Format final Markdown report
    
    Note: Code generation is now on-demand via /generate-patch endpoint
    """
    start_time = time.time()
    
    # Parse repo
    owner, repo = parse_repo(request.repo)
    
    # Clear progress and start new session
    session_id = f"{owner}/{repo}-{int(time.time())}"
    clear_progress(session_id)
    
    # Initialize clients
    github_client = GitHubClient()
    llm_client = get_llm_client()
    
    metadata = {
        "start_time": datetime.utcnow().isoformat(),
        "request": request.model_dump(),
        "session_id": session_id
    }
    
    try:
        # Phase 1: Fetch issues/PRs
        add_progress(f"Fetching items from {owner}/{repo}...", "📥")
        items = await github_client.fetch_all_items(
            owner=owner,
            repo=repo,
            limit=request.limit,
            include_prs=request.include_prs,
            include_issues=request.include_issues
        )
        add_progress(f"Fetched {len(items)} items", "✅")
        metadata["items_fetched"] = len(items)
        
        if not items:
            return TriageResponse(
                repo=request.repo,
                generated_at=datetime.utcnow().isoformat(),
                clusters=[],
                top_issues=[],
                plans=[],
                code_patches=[],
                report_markdown="# No Issues Found\n\nNo open issues or pull requests found in this repository.",
                metadata=metadata
            )
        
        # Phase 2: Summarizer Agent (with ReAct)
        add_progress(f"Running Summarizer agent ({MODEL})", "🤖")
        clusters, summarizer_notes = await cluster_issues(
            items=items,
            github_client=github_client,
            llm_client=llm_client,
            owner=owner,
            repo=repo,
            max_retries=2
        )
        add_progress(f"Created {len(clusters)} clusters", "✅")
        metadata["clusters_count"] = len(clusters)
        metadata["summarizer_notes"] = summarizer_notes
        
        # Phase 3: Labeler Agent (with ReAct)
        add_progress(f"Running Labeler agent ({MODEL})", "🏷️")
        clusters = await label_clusters(
            clusters=clusters,
            items=items,
            github_client=github_client,
            llm_client=llm_client,
            owner=owner,
            repo=repo,
            max_retries=2
        )
        add_progress("Labels suggested", "✅")
        
        # Phase 4: Prioritizer Agent
        add_progress(f"Running Prioritizer agent ({MODEL})", "📊")
        priorities = await prioritize_issues(
            items=items,
            clusters=clusters,
            llm_client=llm_client
        )
        add_progress(f"Prioritized top {len(priorities)} issues", "✅")
        metadata["priorities_count"] = len(priorities)
        
        # Phase 5: Fix-Plan Agent
        add_progress(f"Running Fix-Plan agent ({MODEL})", "🔧")
        plans = await generate_fix_plans(
            priorities=priorities,
            items=items,
            llm_client=llm_client
        )
        add_progress(f"Generated {len(plans)} fix plans", "✅")
        metadata["plans_count"] = len(plans)
        
        # Phase 6: Code Generator Agent is now ON-DEMAND via /generate-patch endpoint
        code_patches = []  # Empty by default, user will request generation
        metadata["code_patches_count"] = 0
        metadata["code_generation_mode"] = "on-demand"
        
        # Phase 7: Editor Agent
        add_progress(f"Running Editor agent ({MODEL})", "📝")
        report_markdown = await format_report(
            repo=request.repo,
            clusters=clusters,
            priorities=priorities,
            plans=plans,
            code_patches=code_patches,
            llm_client=llm_client,
            metadata=metadata
        )
        add_progress("Report formatted", "✅")
        
        # Calculate total time
        elapsed_time = time.time() - start_time
        metadata["elapsed_seconds"] = round(elapsed_time, 2)
        metadata["end_time"] = datetime.utcnow().isoformat()
        
        add_progress(f"Triage complete in {elapsed_time:.2f}s", "🎉")
        
        # Return final response
        return TriageResponse(
            repo=request.repo,
            generated_at=datetime.utcnow().isoformat(),
            clusters=clusters,
            top_issues=priorities,
            plans=plans,
            code_patches=code_patches,
            report_markdown=report_markdown,
            metadata=metadata
        )
    
    finally:
        # Cleanup
        await github_client.close()


def parse_repo(repo: str) -> Tuple[str, str]:
    """
    Parse 'owner/name' format
    
    Returns:
        (owner, repo_name) tuple
    """
    parts = repo.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repo format: {repo}. Expected 'owner/name'")
    return parts[0], parts[1]

