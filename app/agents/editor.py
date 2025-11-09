"""
Editor Agent - Formats final Markdown report
"""
import json
from typing import List
from datetime import datetime
from app.schemas.outputs import Cluster, PriorityEntry, FixPlan, CodePatch
from app.llm import LLMClient


EDITOR_PROMPT = """You are a technical editor.

Your task is to create a clean, professional Markdown report from the triage results.

The report should include:
1. Executive summary
2. Clusters overview (with members and labels)
3. Top 3 prioritized issues with scores
4. Detailed fix plans for each top issue
5. **NEW**: Generated code patches (if available) with confidence scores
6. All claims must cite GitHub URLs

Format the report in clean Markdown with:
- Clear headers (##, ###)
- Bullet lists for clusters and steps
- Tables for priorities
- Code blocks for patches (use ```language syntax)
- Confidence indicators for code patches (🟢 high >0.7, 🟡 medium 0.5-0.7, 🔴 low <0.5)
- Links to all issues

Output ONLY the Markdown text, no JSON wrapper."""


async def format_report(
    repo: str,
    clusters: List[Cluster],
    priorities: List[PriorityEntry],
    plans: List[FixPlan],
    code_patches: List[CodePatch],
    llm_client: LLMClient,
    metadata: dict
) -> str:
    """
    Format the final Markdown report
    """
    # Prepare data
    data = {
        "repo": repo,
        "generated_at": datetime.utcnow().isoformat(),
        "clusters": [c.model_dump() for c in clusters],
        "priorities": [p.model_dump() for p in priorities],
        "plans": [p.model_dump() for p in plans],
        "code_patches": [cp.model_dump() for cp in code_patches],
        "metadata": metadata
    }
    
    messages = [
        {"role": "system", "content": EDITOR_PROMPT},
        {"role": "user", "content": f"Create a professional triage report from this data:\n\n{json.dumps(data, indent=2)}"}
    ]
    
    response = await llm_client.completion(messages, temperature=0.5, max_tokens=4096)
    
    # Extract content
    markdown = response["choices"][0]["message"]["content"]
    
    # Clean up markdown code blocks if present
    if "```markdown" in markdown:
        markdown = markdown.split("```markdown")[1].split("```")[0].strip()
    elif "```" in markdown:
        markdown = markdown.split("```")[1].split("```")[0].strip()
    
    return markdown

