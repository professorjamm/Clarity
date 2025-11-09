"""
Labeler Agent - Suggests labels for clusters with ReAct pattern
"""
import json
from typing import List, Dict, Any
from app.schemas.outputs import FetchedItem, Cluster
from app.llm import LLMClient
from app.tools.github import GitHubClient


LABELER_PROMPT = """You are a GitHub repository labeler.

Your task is to suggest appropriate labels for each cluster of issues/PRs.

Rules:
1. Prefer existing labels if they fit well
2. Suggest 1-4 labels per cluster
3. Use conventional formats:
   - type:bug, type:feature, type:docs, type:refactor
   - component:api, component:ui, component:auth, component:db
   - priority:high, priority:medium, priority:low
   - good-first-issue (for beginner-friendly issues)
4. Compute uncertainty (0.0-1.0) for each cluster's labels
5. If uncertainty > 0.35, note which issues need comments/reviews for better context

Output ONLY valid JSON in this exact format:
{
  "labels_by_cluster": [
    {
      "cluster_id": "cluster_1",
      "labels": ["type:bug", "component:api"],
      "uncertainty": 0.2
    }
  ],
  "needs_context": [123, 456],
  "notes": ["Explanation if needed"]
}"""


async def label_clusters(
    clusters: List[Cluster],
    items: List[FetchedItem],
    github_client: GitHubClient,
    llm_client: LLMClient,
    owner: str,
    repo: str,
    max_retries: int = 2
) -> List[Cluster]:
    """
    Add labels to clusters using ReAct pattern
    
    Returns:
        Updated clusters with proposed_labels filled in
    """
    # Prepare data for LLM
    clusters_json = [c.model_dump() for c in clusters]
    items_json = [item.model_dump() for item in items]
    
    # Get unique existing labels from items
    existing_labels = set()
    for item in items:
        existing_labels.update(item.labels)
    
    messages = [
        {"role": "system", "content": LABELER_PROMPT},
        {"role": "user", "content": f"Existing labels in repo: {list(existing_labels)}\n\nClusters:\n{json.dumps(clusters_json, indent=2)}\n\nAll items:\n{json.dumps(items_json, indent=2)}"}
    ]
    
    response = await llm_client.completion_json(messages, temperature=0.7)
    
    labels_by_cluster = response.get("labels_by_cluster", [])
    needs_context = response.get("needs_context", [])
    
    # ReAct: Check if we need more context
    retry_count = 0
    while needs_context and retry_count < max_retries:
        print(f"🔄 Labeler ReAct: Fetching context for {len(needs_context)} issues...")
        
        # Act: Fetch comments AND reviews (for PRs)
        comments_data = await github_client.batch_fetch_comments(owner, repo, needs_context)
        
        # Separate PRs and fetch reviews
        pr_numbers = [item.number for item in items if item.type == "pr" and item.number in needs_context]
        reviews_data = await github_client.batch_fetch_reviews(owner, repo, pr_numbers) if pr_numbers else {}
        
        # Prepare enhanced context
        enhanced_context = []
        for issue_num in needs_context:
            ctx = {"issue_number": issue_num}
            
            if issue_num in comments_data and comments_data[issue_num]:
                comment_texts = [c.get("body", "")[:150] for c in comments_data[issue_num][:2]]
                ctx["sample_comments"] = comment_texts
            
            if issue_num in reviews_data and reviews_data[issue_num]:
                review_states = [r.get("state", "") for r in reviews_data[issue_num]]
                ctx["review_states"] = review_states
            
            enhanced_context.append(ctx)
        
        # Observe & Refine
        messages.append({"role": "assistant", "content": json.dumps(response)})
        messages.append({
            "role": "user",
            "content": f"Additional context:\n\n{json.dumps(enhanced_context, indent=2)}\n\nPlease refine the labels."
        })
        
        response = await llm_client.completion_json(messages, temperature=0.7)
        labels_by_cluster = response.get("labels_by_cluster", [])
        needs_context = response.get("needs_context", [])
        
        retry_count += 1
    
    # Update clusters with labels
    label_map = {item["cluster_id"]: item for item in labels_by_cluster}
    
    updated_clusters = []
    for cluster in clusters:
        if cluster.id in label_map:
            cluster.proposed_labels = label_map[cluster.id].get("labels", [])
            cluster.uncertainty = min(cluster.uncertainty, label_map[cluster.id].get("uncertainty", 0.5))
        updated_clusters.append(cluster)
    
    return updated_clusters

