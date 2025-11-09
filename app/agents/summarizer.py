"""
Summarizer Agent - Clusters issues by topic with ReAct pattern
"""
import json
from typing import List, Dict, Any, Tuple
from app.schemas.outputs import FetchedItem, Cluster
from app.llm import LLMClient
from app.tools.github import GitHubClient


SUMMARIZER_PROMPT = """You are the Summarizer/Clusterer for GitHub repositories.

Your task is to analyze GitHub issues and pull requests, then group them into meaningful topic clusters.

Rules:
1. Cluster by concrete, technical topics (e.g., "Authentication Errors", "TypeScript Migration", "Performance Issues")
2. Merge near-duplicates and related issues into the same cluster
3. Create 3-7 clusters maximum (unless there are truly distinct topics)
4. Compute an uncertainty score (0.0 to 1.0) for each cluster:
   - 0.0 = very confident about clustering
   - 0.5 = moderate uncertainty
   - 1.0 = very uncertain, need more context
5. If uncertainty > 0.4 for any cluster, note which issue numbers need comments/reviews fetched

Output ONLY valid JSON in this exact format:
{
  "clusters": [
    {
      "id": "cluster_1",
      "title": "Descriptive Cluster Title",
      "summary": "A 3-5 line summary of what these issues are about and their common theme.",
      "members": [123, 456, 789],
      "proposed_labels": [],
      "uncertainty": 0.3
    }
  ],
  "needs_context": [123, 456],
  "notes": ["Explanation of why context is needed"]
}"""


async def cluster_issues(
    items: List[FetchedItem],
    github_client: GitHubClient,
    llm_client: LLMClient,
    owner: str,
    repo: str,
    max_retries: int = 2
) -> Tuple[List[Cluster], List[str]]:
    """
    Cluster issues using ReAct pattern
    
    Returns:
        (clusters, notes) tuple
    """
    # Prepare items for LLM
    items_json = [item.model_dump() for item in items]
    
    # Initial reasoning pass
    messages = [
        {"role": "system", "content": SUMMARIZER_PROMPT},
        {"role": "user", "content": f"Cluster these issues/PRs:\n\n{json.dumps(items_json, indent=2)}"}
    ]
    
    response = await llm_client.completion_json(messages, temperature=0.7)
    
    # Parse initial response
    clusters_data = response.get("clusters", [])
    needs_context = response.get("needs_context", [])
    notes = response.get("notes", [])
    
    # ReAct: Check if we need more context
    retry_count = 0
    while needs_context and retry_count < max_retries:
        print(f"🔄 Summarizer ReAct: Fetching comments for {len(needs_context)} issues...")
        
        # Act: Fetch comments for uncertain issues
        comments_data = await github_client.batch_fetch_comments(owner, repo, needs_context)
        
        # Prepare enhanced context
        enhanced_context = []
        for issue_num, comments in comments_data.items():
            if comments:
                comment_texts = [c.get("body", "")[:200] for c in comments[:3]]  # First 3 comments
                enhanced_context.append({
                    "issue_number": issue_num,
                    "sample_comments": comment_texts
                })
        
        # Observe & Refine: Re-run with additional context
        messages.append({
            "role": "assistant",
            "content": json.dumps(response)
        })
        messages.append({
            "role": "user",
            "content": f"Here is additional context from comments:\n\n{json.dumps(enhanced_context, indent=2)}\n\nPlease refine the clusters with this new information."
        })
        
        response = await llm_client.completion_json(messages, temperature=0.7)
        clusters_data = response.get("clusters", [])
        needs_context = response.get("needs_context", [])
        notes = response.get("notes", [])
        
        retry_count += 1
    
    # Convert to Cluster objects
    clusters = []
    for c in clusters_data:
        try:
            cluster = Cluster(
                id=c.get("id", f"cluster_{len(clusters)}"),
                title=c.get("title", "Untitled Cluster"),
                summary=c.get("summary", ""),
                members=c.get("members", []),
                proposed_labels=c.get("proposed_labels", []),
                uncertainty=c.get("uncertainty", 0.5)
            )
            clusters.append(cluster)
        except Exception as e:
            print(f"Error parsing cluster: {e}")
            continue
    
    return clusters, notes

