"""
Fix-Plan Agent - Generates actionable fix plans for top issues
"""
import json
from typing import List
from app.schemas.outputs import FetchedItem, PriorityEntry, FixPlan
from app.llm import LLMClient


FIX_PLAN_PROMPT = """You are a senior software engineer creating fix plans.

Your task is to create detailed, actionable plans for fixing issues.

For each issue, provide:
1. Step-by-step plan (5-9 concrete steps)
2. Files likely to be touched (educated guesses based on issue description)
3. Edge cases to consider
4. Acceptance criteria (what "done" looks like)
5. Test hints (what to test)
6. Citations (GitHub URLs)

Be specific and technical. If the issue mentions files, components, or error messages, reference them.

Output ONLY valid JSON in this exact format:
{
  "plans": [
    {
      "number": 123,
      "title": "Issue title",
      "plan": [
        "Step 1: Identify the root cause...",
        "Step 2: Modify the authentication handler...",
        "Step 3: Add validation...",
        "Step 4: Update tests...",
        "Step 5: Deploy and verify..."
      ],
      "files_likely_touched": [
        "src/auth/handler.ts",
        "src/middleware/auth.ts",
        "tests/auth.test.ts"
      ],
      "edge_cases": [
        "User already logged in",
        "Expired tokens",
        "Concurrent login attempts"
      ],
      "acceptance_criteria": [
        "Users can log in successfully",
        "Error messages are clear",
        "No regression in existing auth flows"
      ],
      "test_hints": [
        "Test login with valid credentials",
        "Test login with invalid credentials",
        "Test token expiration",
        "Load test with 100 concurrent users"
      ],
      "citations": ["https://github.com/owner/repo/issues/123"]
    }
  ]
}"""


async def generate_fix_plans(
    priorities: List[PriorityEntry],
    items: List[FetchedItem],
    llm_client: LLMClient
) -> List[FixPlan]:
    """
    Generate fix plans for prioritized issues
    """
    # Get full details for prioritized issues
    priority_numbers = [p.number for p in priorities]
    relevant_items = [item for item in items if item.number in priority_numbers]
    
    # Prepare data for LLM
    priorities_json = [p.model_dump() for p in priorities]
    items_json = [item.model_dump() for item in relevant_items]
    
    messages = [
        {"role": "system", "content": FIX_PLAN_PROMPT},
        {"role": "user", "content": f"Create fix plans for these prioritized issues:\n\nPriorities:\n{json.dumps(priorities_json, indent=2)}\n\nFull issue details:\n{json.dumps(items_json, indent=2)}"}
    ]
    
    response = await llm_client.completion_json(messages, temperature=0.6, max_tokens=4096)
    
    # Parse response
    plans_data = response.get("plans", [])
    
    # Convert to FixPlan objects
    plans = []
    for plan_data in plans_data:
        try:
            plan = FixPlan(
                number=plan_data.get("number"),
                title=plan_data.get("title", ""),
                plan=plan_data.get("plan", []),
                files_likely_touched=plan_data.get("files_likely_touched", []),
                edge_cases=plan_data.get("edge_cases", []),
                acceptance_criteria=plan_data.get("acceptance_criteria", []),
                test_hints=plan_data.get("test_hints", []),
                citations=plan_data.get("citations", [])
            )
            plans.append(plan)
        except Exception as e:
            print(f"Error parsing fix plan: {e}")
            continue
    
    return plans

