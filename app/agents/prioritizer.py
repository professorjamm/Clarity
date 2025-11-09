"""
Prioritizer Agent - Scores and selects top 3 issues
"""
import json
from typing import List
from app.schemas.outputs import FetchedItem, Cluster, PriorityEntry
from app.llm import LLMClient


PRIORITIZER_PROMPT = """You are an engineering triage lead.

Your task is to score and prioritize issues/PRs based on their importance and urgency.

Scoring criteria:
1. Severity (1-5): How badly does this affect users?
   - 5: Critical bug, system down, data loss
   - 4: Major bug, feature broken
   - 3: Moderate issue, workaround exists
   - 2: Minor bug, cosmetic issue
   - 1: Enhancement, nice-to-have

2. Impact (1-5): How many users are affected?
   - 5: All users
   - 4: Most users
   - 3: Many users
   - 2: Some users
   - 1: Few users

3. Effort (1-5): How hard is it to fix?
   - 5: Requires major refactor, weeks of work
   - 4: Significant changes, days of work
   - 3: Moderate changes, hours of work
   - 2: Small changes, quick fix
   - 1: Trivial fix, minutes

Formula: score = clamp((severity*4 + impact*3 - effort*2)*3, 0, 100)

Select the TOP 3 issues with the highest scores and provide justifications.

Output ONLY valid JSON in this exact format:
{
  "top": [
    {
      "number": 123,
      "title": "Issue title",
      "severity": 4,
      "impact": 4,
      "effort": 2,
      "score": 78,
      "justification": "Brief explanation of why this is prioritized",
      "links": ["https://github.com/owner/repo/issues/123"]
    }
  ]
}"""


async def prioritize_issues(
    items: List[FetchedItem],
    clusters: List[Cluster],
    llm_client: LLMClient
) -> List[PriorityEntry]:
    """
    Prioritize issues and return Top 3
    """
    # Prepare data for LLM
    items_json = [item.model_dump() for item in items]
    clusters_json = [c.model_dump() for c in clusters]
    
    messages = [
        {"role": "system", "content": PRIORITIZER_PROMPT},
        {"role": "user", "content": f"Clusters:\n{json.dumps(clusters_json, indent=2)}\n\nAll items:\n{json.dumps(items_json, indent=2)}\n\nSelect and score the TOP 3 most important issues to address."}
    ]
    
    response = await llm_client.completion_json(messages, temperature=0.5)
    
    # Parse response
    top_items = response.get("top", [])
    
    # Convert to PriorityEntry objects
    priorities = []
    for item in top_items[:3]:  # Ensure only top 3
        try:
            priority = PriorityEntry(
                number=item.get("number"),
                title=item.get("title", ""),
                severity=item.get("severity", 3),
                impact=item.get("impact", 3),
                effort=item.get("effort", 3),
                score=item.get("score", 50.0),
                justification=item.get("justification", ""),
                links=item.get("links", [])
            )
            priorities.append(priority)
        except Exception as e:
            print(f"Error parsing priority entry: {e}")
            continue
    
    return priorities

