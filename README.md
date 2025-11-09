# Clarity - AI-Powered GitHub Issue Triage System

> Multi-agent system for intelligent GitHub repository analysis with automated code generation

**Built with NVIDIA Nemotron for the Nemotron Prize Track**

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [APIs Used](#apis-used)
4. [Communication Flow](#communication-flow)
5. [Complete Workflow](#complete-workflow)
6. [Models & Why We Chose Them](#models--why-we-chose-them)
7. [Agent Deep Dive](#agent-deep-dive)
8. [Setup & Installation](#setup--installation)
9. [Usage Guide](#usage-guide)
10. [Technical Details](#technical-details)

---

## Project Overview

**Clarity** is an intelligent issue triage system that automates the tedious process of analyzing GitHub repositories. It uses a **6-agent multi-agent architecture** powered by NVIDIA Nemotron to:

- **Cluster issues** by technical topics
- **Suggest labels** for better organization
- **Prioritize issues** based on severity, impact, and effort
- **Generate fix plans** with actionable steps
- **Generate code patches** on-demand for top issues
- **Format professional reports** in Markdown

### Key Features

✅ **Multi-Agent Architecture**: 6 specialized AI agents working together  
✅ **ReAct Pattern**: Agents can fetch additional context when uncertain  
✅ **Interactive Code Generation**: On-demand code fixes for prioritized issues  
✅ **Modern Web UI**: Dark, minimalist interface with real-time progress  
✅ **Production-Ready**: Full REST API, error handling, caching  

---

## Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Server                            │
│                         (app/app.py)                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator (router.py)                      │
│         Coordinates all agents and manages workflow              │
└────────┬────────────────────────────────────────────────────────┘
         │
         ├──► GitHub API Client ──► Fetches issues/PRs/comments
         │
         └──► LLM Client (NVIDIA NIM) ──► Powers all 6 agents
                       │
                       ▼
         ┌─────────────────────────────┐
         │      6 AI AGENTS             │
         │  1. Summarizer               │
         │  2. Labeler                  │
         │  3. Prioritizer              │
         │  4. Fix-Plan                 │
         │  5. Code Generator           │
         │  6. Editor                   │
         └─────────────────────────────┘
```

### Component Architecture

```
app/
├── app.py                 # FastAPI server & web UI
├── router.py              # Orchestration & workflow control
├── llm.py                 # NVIDIA NIM LLM client
├── llm_openrouter.py      # Alternative LLM client (OpenRouter)
│
├── agents/                # AI Agent implementations
│   ├── summarizer.py      # Clusters issues by topic
│   ├── labeler.py         # Suggests labels for clusters
│   ├── prioritizer.py     # Scores & ranks issues
│   ├── fix_plan.py        # Generates actionable fix plans
│   ├── code_generator.py  # Generates code patches
│   └── editor.py          # Formats final Markdown reports
│
├── tools/                 # External API integrations
│   ├── github.py          # GitHub REST API client
│   └── cache.py           # In-memory TTL cache
│
└── schemas/               # Pydantic data models
    ├── inputs.py          # Request schemas
    └── outputs.py         # Response schemas
```

---

## APIs Used

### 1. GitHub REST API

**Purpose**: Fetch repository data (issues, PRs, comments, reviews)

**Base URL**: `https://api.github.com`

**Key Endpoints Used**:

| Endpoint | Purpose | Agent(s) Using It |
|----------|---------|-------------------|
| `GET /repos/{owner}/{repo}/issues` | Fetch all issues & PRs | Orchestrator |
| `GET /repos/{owner}/{repo}/issues/{number}/comments` | Fetch issue comments | Summarizer, Labeler |
| `GET /repos/{owner}/{repo}/pulls/{number}/reviews` | Fetch PR reviews | Labeler |

**Authentication**: 
- Optional GitHub token via `Authorization: Bearer {token}` header
- Without token: 60 requests/hour
- With token: 5,000 requests/hour

**Implementation**: `app/tools/github.py` - `GitHubClient` class

**Caching Strategy**: 
- 5-minute TTL in-memory cache
- Reduces API calls during agent retries
- Cache key: full URL with query params

---

### 2. NVIDIA NIM API (Nemotron)

**Purpose**: Power all AI agents with reasoning capabilities

**Base URL**: `https://integrate.api.nvidia.com/v1`

**Model**: `nvidia/nvidia-nemotron-nano-9b-v2`

**Key Endpoint**:

```
POST /chat/completions
Content-Type: application/json
Authorization: Bearer {NVIDIA_API_KEY}

{
  "model": "nvidia/nvidia-nemotron-nano-9b-v2",
  "messages": [...],
  "temperature": 0.7,
  "max_tokens": 4096,
  "extra_body": {
    "min_thinking_tokens": 1024,
    "max_thinking_tokens": 2048
  }
}
```

**Special Features Used**:
- **Thinking Tokens**: Enables deeper reasoning (1024-2048 tokens)
- **JSON Mode**: Structured outputs for parsing
- **Tool Calling**: Function calling for ReAct pattern

**Authentication**: API key via `NVIDIA_API_KEY` environment variable

**Implementation**: `app/llm.py` - `LLMClient` class

**Alternative**: `app/llm_openrouter.py` provides OpenRouter fallback if NVIDIA API access is limited

---

### 3. Alternative: OpenRouter API (Optional)

**Purpose**: Fallback for Nemotron access via OpenRouter

**Base URL**: `https://openrouter.ai/api/v1`

**Model**: `nvidia/llama-3.1-nemotron-70b-instruct`

**Why**: Some NVIDIA API keys don't have Nemotron access - OpenRouter provides alternative access

**Authentication**: `OPENROUTER_API_KEY` environment variable

---

## Communication Flow

### Request-Response Flow

```
1. User Request (Web UI or API)
   ↓
2. FastAPI Endpoint (/triage)
   ↓
3. Orchestrator (router.py)
   │
   ├──► Fetch GitHub Data
   │    ├── List issues/PRs
   │    └── Return FetchedItem[]
   │
   ├──► Agent 1: Summarizer
   │    ├── Send items to LLM
   │    ├── LLM returns clusters with uncertainty
   │    ├── If uncertain → fetch comments via GitHub API
   │    └── Return Cluster[]
   │
   ├──► Agent 2: Labeler
   │    ├── Send clusters + items to LLM
   │    ├── LLM suggests labels with uncertainty
   │    ├── If uncertain → fetch comments/reviews
   │    └── Return updated Cluster[] with labels
   │
   ├──► Agent 3: Prioritizer
   │    ├── Send all data to LLM
   │    ├── LLM scores each issue
   │    └── Return top 3 PriorityEntry[]
   │
   ├──► Agent 4: Fix-Plan
   │    ├── Send top issues to LLM
   │    ├── LLM generates step-by-step plans
   │    └── Return FixPlan[]
   │
   ├──► Agent 5: Code Generator (ON-DEMAND)
   │    ├── User clicks "Generate Code Fix"
   │    ├── POST /generate-patch with issue data
   │    ├── LLM generates pseudocode + full code
   │    └── Return CodePatch with confidence
   │
   └──► Agent 6: Editor
        ├── Send all results to LLM
        ├── LLM formats Markdown report
        └── Return formatted report
   ↓
4. FastAPI returns TriageResponse
   ↓
5. Web UI displays results
```

### Data Flow Between Components

```
GitHub API          LLM API (NVIDIA NIM)         Agents
    │                       │                       │
    │  1. Fetch Issues      │                       │
    │◄──────────────────────┤                       │
    │                       │                       │
    │                       │  2. Cluster Issues    │
    ├───────────────────────┼──────────────────────►│
    │                       │◄──────────────────────┤
    │                       │                       │
    │  3. Fetch Comments    │  (if uncertain)       │
    │◄──────────────────────┤◄──────────────────────┤
    │                       │                       │
    │                       │  4. Refine Clusters   │
    ├───────────────────────┼──────────────────────►│
    │                       │◄──────────────────────┤
    │                       │                       │
    │                       │  5. Label Clusters    │
    ├───────────────────────┼──────────────────────►│
    │                       │◄──────────────────────┤
    │                       │                       │
    │                       │  6. Prioritize        │
    ├───────────────────────┼──────────────────────►│
    │                       │◄──────────────────────┤
    │                       │                       │
    │                       │  7. Generate Plans    │
    ├───────────────────────┼──────────────────────►│
    │                       │◄──────────────────────┤
    │                       │                       │
    │                       │  8. Format Report     │
    ├───────────────────────┼──────────────────────►│
    │                       │◄──────────────────────┤
```

---

## Complete Workflow

### Phase 1: Data Acquisition

**Orchestrator** (`router.py:51`)

1. Parse repository name (`owner/repo`)
2. Initialize GitHub client
3. Initialize LLM client
4. Fetch issues and PRs:
   ```python
   items = await github_client.fetch_all_items(
       owner=owner,
       repo=repo,
       limit=50,
       include_prs=True,
       include_issues=True
   )
   ```
5. Convert to `FetchedItem` objects with standardized schema

**Output**: List of `FetchedItem` objects

---

### Phase 2: Issue Clustering (Summarizer Agent)

**Agent**: Summarizer (`app/agents/summarizer.py`)

**Input**: List of `FetchedItem` objects

**Process**:

1. **Initial Reasoning**:
   - Send all items to LLM with clustering prompt
   - LLM analyzes titles, bodies, labels
   - LLM creates 3-7 clusters by topic
   - LLM assigns uncertainty score (0.0-1.0) to each cluster

2. **ReAct Loop** (if uncertainty > 0.4):
   - Identify issues needing more context
   - **Action**: Fetch comments via GitHub API
   - **Observation**: Analyze comment content
   - **Refinement**: Re-cluster with new context
   - Max 2 retries

3. **Validation**:
   - Ensure no orphaned issues
   - Merge duplicate clusters
   - Validate cluster sizes

**Output**: List of `Cluster` objects

**Example Cluster**:
```json
{
  "id": "cluster_1",
  "title": "Authentication Errors",
  "summary": "Issues related to login failures, token expiration, and OAuth bugs",
  "members": [123, 456, 789],
  "proposed_labels": [],
  "uncertainty": 0.3
}
```

---

### Phase 3: Label Suggestion (Labeler Agent)

**Agent**: Labeler (`app/agents/labeler.py`)

**Input**: Clusters + Items

**Process**:

1. **Analysis**:
   - Extract existing labels from repository
   - Analyze cluster topics and member issues
   - Suggest 1-4 labels per cluster
   - Follow conventions: `type:*`, `component:*`, `priority:*`

2. **ReAct Loop** (if uncertainty > 0.35):
   - **Action**: Fetch comments for uncertain issues
   - **Action**: Fetch PR reviews if applicable
   - **Observation**: Analyze review states (APPROVED, CHANGES_REQUESTED)
   - **Refinement**: Update label suggestions

**Output**: Updated `Cluster` objects with `proposed_labels`

**Example Labels**:
```json
{
  "cluster_id": "cluster_1",
  "labels": ["type:bug", "component:auth", "priority:high"],
  "uncertainty": 0.2
}
```

---

### Phase 4: Issue Prioritization (Prioritizer Agent)

**Agent**: Prioritizer (`app/agents/prioritizer.py`)

**Input**: All items + Clusters

**Process**:

1. **Scoring Formula**:
   ```
   score = clamp((severity*4 + impact*3 - effort*2)*3, 0, 100)
   ```

   Where:
   - **Severity** (1-5): How badly does this affect users?
     - 5 = Critical (system down, data loss)
     - 4 = Major (feature broken)
     - 3 = Moderate (workaround exists)
     - 2 = Minor (cosmetic)
     - 1 = Enhancement

   - **Impact** (1-5): How many users affected?
     - 5 = All users
     - 4 = Most users
     - 3 = Many users
     - 2 = Some users
     - 1 = Few users

   - **Effort** (1-5): How hard to fix?
     - 5 = Major refactor (weeks)
     - 4 = Significant changes (days)
     - 3 = Moderate changes (hours)
     - 2 = Small changes (quick)
     - 1 = Trivial (minutes)

2. **Selection**:
   - LLM scores all issues
   - Sorts by score (descending)
   - Selects top 3 issues
   - Provides justification for each

**Output**: List of top 3 `PriorityEntry` objects

**Example Priority**:
```json
{
  "number": 123,
  "title": "Login fails with expired tokens",
  "severity": 4,
  "impact": 5,
  "effort": 2,
  "score": 87,
  "justification": "Critical bug affecting all users, but has a quick fix",
  "links": ["https://github.com/owner/repo/issues/123"]
}
```

---

### Phase 5: Fix Plan Generation (Fix-Plan Agent)

**Agent**: Fix-Plan (`app/agents/fix_plan.py`)

**Input**: Top 3 prioritized issues

**Process**:

1. **Plan Structure**:
   - 5-9 concrete steps
   - Files likely to be modified
   - Edge cases to consider
   - Acceptance criteria
   - Test hints

2. **LLM Analysis**:
   - Read issue description carefully
   - Infer codebase structure from mentions
   - Generate specific, actionable steps
   - Suggest file paths (educated guesses)

**Output**: List of `FixPlan` objects

**Example Fix Plan**:
```json
{
  "number": 123,
  "title": "Login fails with expired tokens",
  "plan": [
    "Step 1: Add token expiration validation in auth middleware",
    "Step 2: Implement token refresh logic",
    "Step 3: Update error messages for clarity",
    "Step 4: Add unit tests for token validation",
    "Step 5: Deploy and monitor error rates"
  ],
  "files_likely_touched": [
    "src/auth/middleware.ts",
    "src/auth/token.ts",
    "tests/auth.test.ts"
  ],
  "edge_cases": [
    "Concurrent login attempts",
    "Token expires mid-request",
    "Refresh token also expired"
  ],
  "acceptance_criteria": [
    "Users redirected to login on token expiry",
    "Clear error messages displayed",
    "No data loss on session timeout"
  ],
  "test_hints": [
    "Test with manually expired token",
    "Test token refresh flow",
    "Load test with 100 concurrent users"
  ]
}
```

---

### Phase 6: Code Generation (Code Generator Agent) - ON-DEMAND

**Agent**: Code Generator (`app/agents/code_generator.py`)

**Trigger**: User clicks "Generate Code Fix" button in UI

**Input**: Priority entry + Fix plan + Full issue details

**Process**:

1. **Context Preparation**:
   - Extract issue body (first 1000 chars)
   - Include fix plan steps
   - Include file paths from fix plan
   - Include edge cases and acceptance criteria

2. **LLM Generation**:
   - **Pseudocode**: Explanatory code with inline comments
     - Uses `///` comments to explain each step
     - Focuses on clarity and educational value
     - Helps developer understand WHY each change is needed
   
   - **Full Code** (optional): Complete AI-generated implementation
     - Hidden by default in UI
     - User can toggle to view
     - Includes proper types, error handling

3. **Confidence Scoring**:
   - 0.7-1.0 (High): Strong confidence, clear path
   - 0.5-0.7 (Medium): Reasonable confidence, some assumptions
   - 0.3-0.5 (Low): Uncertain, needs review
   - < 0.3: Rejected, not shown

**Output**: `CodePatch` object

**Example Code Patch**:
```json
{
  "issue_number": 123,
  "file_path": "src/auth/middleware.ts",
  "pseudocode": "/// Add token expiration check\nfunction validateToken(token) {\n  /// Check if token exists\n  if (!token) throw new Error('No token');\n  /// Verify expiration time\n  if (token.exp < Date.now()) {\n    throw new Error('Token expired');\n  }\n  /// Continue validation\n  return verifySignature(token);\n}",
  "explanation": "Adds token expiration validation to prevent expired tokens from being processed.",
  "confidence": 0.85,
  "approach": "defensive-validation",
  "notes": "Integrate with your existing auth error handling.",
  "full_code": "function validateToken(token: AuthToken): boolean {\n  if (!token || !token.exp) {\n    throw new AuthenticationError('Invalid token structure');\n  }\n  if (token.exp < Date.now()) {\n    throw new TokenExpiredError('Token has expired');\n  }\n  return verifyTokenSignature(token);\n}"
}
```

---

### Phase 7: Report Formatting (Editor Agent)

**Agent**: Editor (`app/agents/editor.py`)

**Input**: All results (clusters, priorities, plans, patches)

**Process**:

1. **Structure**:
   - Executive summary
   - Cluster overview with labels
   - Top 3 issues table
   - Detailed fix plans
   - Code patches with confidence indicators
   - All citations to GitHub URLs

2. **Formatting**:
   - Clean Markdown syntax
   - Headers (##, ###)
   - Tables for priorities
   - Code blocks with language tags
   - Links to all issues

**Output**: Formatted Markdown report

**Example Report Structure**:
```markdown
# Triage Report: owner/repo

## Executive Summary
Analyzed 50 issues/PRs, identified 5 clusters, prioritized top 3 issues.

## Clusters
### 1. Authentication Errors (8 issues)
- Labels: type:bug, component:auth, priority:high
- Members: #123, #456, #789...

## Top Priority Issues
| # | Title | Severity | Impact | Effort | Score |
|---|-------|----------|--------|--------|-------|
| 123 | Login fails | 4 | 5 | 2 | 87 |

## Fix Plans
### Issue #123: Login fails with expired tokens
**Plan:**
1. Add token expiration validation...
```

---

### Phase 8: Response Delivery

**Orchestrator** returns `TriageResponse`:

```json
{
  "repo": "owner/repo",
  "generated_at": "2024-01-01T12:00:00Z",
  "clusters": [...],
  "top_issues": [...],
  "plans": [...],
  "code_patches": [],
  "report_markdown": "# Triage Report...",
  "metadata": {
    "elapsed_seconds": 45.2,
    "items_fetched": 50,
    "clusters_count": 5,
    "code_generation_mode": "on-demand"
  }
}
```

Web UI displays results with interactive code generation.

---

## Models & Why We Chose Them

### Primary Model: NVIDIA Nemotron Nano 9B v2

**Model ID**: `nvidia/nvidia-nemotron-nano-9b-v2`

**Why This Model?**

1. **Reasoning Excellence**:
   - Optimized for multi-step reasoning tasks
   - Extended thinking tokens (1024-2048) enable deeper analysis
   - Perfect for complex triage decisions

2. **Efficiency**:
   - 9B parameters = fast inference
   - Critical for multi-agent workflows (6+ LLM calls per request)
   - Reduces latency for user-facing application

3. **Technical Focus**:
   - Fine-tuned for engineering/technical content
   - Understands code, bug reports, technical terminology
   - Better at parsing GitHub issue descriptions

4. **Function Calling**:
   - Native support for tool calling
   - Essential for ReAct pattern implementation
   - Clean structured outputs (JSON mode)

5. **Cost-Effective**:
   - Smaller than 70B models but comparable quality
   - Lower API costs for high-volume requests
   - Sustainable for production deployment

**Configuration**:
```python
{
  "temperature": 0.7,          # Balanced creativity/consistency
  "max_tokens": 4096,           # Long outputs for fix plans
  "min_thinking_tokens": 1024,  # Deep reasoning
  "max_thinking_tokens": 2048   # Extended analysis
}
```

**Temperature Settings by Agent**:
- **Summarizer**: 0.7 (creative clustering)
- **Labeler**: 0.7 (flexible label suggestions)
- **Prioritizer**: 0.5 (conservative scoring)
- **Fix-Plan**: 0.6 (balanced planning)
- **Code Generator**: 0.4 (precise code generation)
- **Editor**: 0.5 (consistent formatting)

---

### Alternative Model: Nemotron 70B Instruct (via OpenRouter)

**Model ID**: `nvidia/llama-3.1-nemotron-70b-instruct`

**When to Use**:
- NVIDIA API key doesn't have Nano 9B access
- Need higher accuracy for complex repositories
- Have sufficient API budget

**Trade-offs**:
- Higher quality outputs
- Slower inference (~2-3x latency)
- Higher API costs
- Better for large-scale enterprise repos

---

## Agent Deep Dive

### 1. Summarizer Agent

**File**: `app/agents/summarizer.py`

**Purpose**: Cluster issues by technical topics

**Decision-Making Process**:

1. **Initial Analysis**:
   ```python
   # LLM receives all issues/PRs
   # Analyzes: titles, bodies, labels, comment counts
   # Groups by technical similarity
   ```

2. **Clustering Logic**:
   - Looks for keyword patterns (e.g., "auth", "database", "UI")
   - Identifies semantic relationships between issues
   - Merges near-duplicates
   - Creates 3-7 clusters (balance: too few = vague, too many = fragmented)

3. **Uncertainty Detection**:
   ```python
   if cluster.uncertainty > 0.4:
       # Issue titles are ambiguous
       # Need comment context to understand
       fetch_comments(cluster.members)
   ```

4. **ReAct Refinement**:
   - Reads first 3 comments per uncertain issue
   - Extracts key phrases
   - Re-evaluates cluster membership
   - Updates cluster summaries

**Key Prompt Elements**:
- "Cluster by concrete, technical topics"
- "Merge near-duplicates"
- "Compute uncertainty (0.0-1.0)"
- "Note which issues need comments"

**Output**: 3-7 clusters with summaries and uncertainty scores

---

### 2. Labeler Agent

**File**: `app/agents/labeler.py`

**Purpose**: Suggest labels for each cluster

**Decision-Making Process**:

1. **Existing Label Analysis**:
   ```python
   # Extract all labels from repository
   existing_labels = {"bug", "enhancement", "documentation", ...}
   # Prefer existing labels to maintain consistency
   ```

2. **Label Selection**:
   - Follows conventions: `type:*`, `component:*`, `priority:*`
   - Suggests 1-4 labels per cluster
   - Prioritizes existing labels over new ones
   - Uses cluster summary + member issues for context

3. **Uncertainty Triggers**:
   ```python
   if cluster_label_uncertainty > 0.35:
       # Cluster has mixed issue types
       # Need deeper context
       fetch_comments_and_reviews()
   ```

4. **ReAct Refinement**:
   - Fetches comments for uncertain issues
   - Fetches PR reviews (APPROVED, CHANGES_REQUESTED, etc.)
   - Analyzes review states for priority hints
   - Updates label suggestions

**Key Prompt Elements**:
- "Prefer existing labels if they fit"
- "Use conventional formats"
- "Suggest 1-4 labels per cluster"
- "Compute uncertainty for label fit"

**Output**: Clusters with `proposed_labels` array

---

### 3. Prioritizer Agent

**File**: `app/agents/prioritizer.py`

**Purpose**: Score and select top 3 issues

**Decision-Making Process**:

1. **Severity Assessment** (1-5):
   - Searches for keywords: "critical", "crash", "data loss", "security"
   - Analyzes user impact descriptions
   - Considers system-wide effects
   - Weighs reproducibility

2. **Impact Assessment** (1-5):
   - Looks for: "all users", "most users", "everyone"
   - Considers upvotes/reactions (if available)
   - Analyzes comment count as proxy for user impact
   - Weighs PR merge readiness

3. **Effort Estimation** (1-5):
   - Infers from fix plan complexity
   - Looks for: "simple fix", "requires refactor", "needs research"
   - Considers file count in PR diffs
   - Analyzes edge cases mentioned

4. **Scoring Formula**:
   ```python
   score = clamp((severity*4 + impact*3 - effort*2) * 3, 0, 100)
   ```
   - Severity weighted 4x (most important)
   - Impact weighted 3x (second priority)
   - Effort weighted -2x (penalty for complexity)
   - Multiplied by 3 to scale to 0-100

5. **Top 3 Selection**:
   - Sorts all issues by score
   - Takes top 3
   - Ensures diversity (not all from same cluster)
   - Generates justification for each

**Key Prompt Elements**:
- "Score based on severity, impact, effort"
- "Use formula: (severity*4 + impact*3 - effort*2)*3"
- "Select TOP 3 most important"
- "Provide justification for each"

**Output**: Top 3 `PriorityEntry` objects with scores and justifications

---

### 4. Fix-Plan Agent

**File**: `app/agents/fix_plan.py`

**Purpose**: Generate actionable fix plans

**Decision-Making Process**:

1. **Issue Analysis**:
   - Reads full issue body (first 1000 chars)
   - Identifies error messages, stack traces, logs
   - Extracts file paths, line numbers mentioned
   - Notes reproduction steps

2. **Plan Generation**:
   ```python
   # 5-9 concrete steps
   steps = [
       "Step 1: Identify root cause in auth middleware",
       "Step 2: Add token expiration check",
       "Step 3: Implement refresh logic",
       "Step 4: Update error messages",
       "Step 5: Add unit tests",
       "Step 6: Integration test with frontend",
       "Step 7: Deploy to staging",
       "Step 8: Monitor error rates",
       "Step 9: Document the fix"
   ]
   ```

3. **File Path Inference**:
   - Looks for file mentions in issue body
   - Infers from error stack traces
   - Guesses based on common patterns:
     - Auth issues → `src/auth/*`
     - Database issues → `src/db/*`, `models/*`
     - UI issues → `components/*`, `views/*`

4. **Edge Case Identification**:
   - Extracts from comments
   - Infers from issue description
   - Considers common failure modes
   - Examples: concurrency, null values, edge inputs

5. **Test Hint Generation**:
   - Unit tests for core logic
   - Integration tests for workflows
   - Load tests for performance issues
   - Security tests for auth/validation issues

**Key Prompt Elements**:
- "Create detailed, actionable plans"
- "5-9 concrete steps"
- "List files likely to be touched"
- "Consider edge cases"
- "Provide test hints"

**Output**: `FixPlan` objects with steps, files, edge cases, acceptance criteria

---

### 5. Code Generator Agent

**File**: `app/agents/code_generator.py`

**Purpose**: Generate code patches on-demand

**Decision-Making Process**:

1. **Context Assembly**:
   ```python
   context = {
       "issue": {
           "number": 123,
           "title": "Login fails",
           "body": "When users try to login with expired tokens...",
           "severity": 4,
           "impact": 5
       },
       "fix_plan": {
           "steps": [...],
           "files": ["src/auth/middleware.ts"],
           "edge_cases": [...]
       }
   }
   ```

2. **Pseudocode Generation**:
   - Uses `///` for explanatory comments
   - Shows logical structure without exact syntax
   - Focuses on clarity and education
   - Helps developer understand WHY
   - Example:
     ```javascript
     /// Add connection timeout handling
     async function sendRequest(request) {
       /// Create abort controller for timeout
       const controller = new AbortController();
       /// Set timeout to 5 seconds
       setTimeout(() => controller.abort(), 5000);
       /// Attempt request with timeout signal
       try {
         return await fetch(request.url, { signal: controller.signal });
       } catch (error) {
         /// Handle timeout errors appropriately
         if (error.name === 'AbortError') {
           throw new Error('Connection timed out');
         }
         throw error;
       }
     }
     ```

3. **Full Code Generation** (Optional):
   - Complete implementation with proper types
   - Includes error handling
   - Follows language conventions
   - Hidden by default in UI (user can toggle)

4. **Confidence Calculation**:
   ```python
   confidence = calculate_confidence(
       has_file_path=True,        # +0.2
       has_error_message=True,    # +0.2
       has_reproduction_steps=True, # +0.2
       fix_plan_detailed=True,    # +0.2
       edge_cases_identified=True # +0.2
   )
   # Max: 1.0, Min: 0.3 (rejected if < 0.3)
   ```

5. **Quality Checks**:
   - Rejects patches with confidence < 0.3
   - Validates required fields present
   - Ensures code is syntactically valid
   - Checks for security anti-patterns

6. **Fallback Handling**:
   - If JSON parsing fails, extracts raw code
   - Creates basic patch structure
   - Sets confidence to 0.5 (medium)
   - Adds warning note for review

**Key Prompt Elements**:
- "Generate PSEUDOCODE with explanatory comments"
- "Show logical structure, not exact syntax"
- "Focus on clarity and education"
- "Optionally provide full code implementation"
- "Include confidence score"

**Output**: `CodePatch` with pseudocode, explanation, confidence, and optional full code

---

### 6. Editor Agent

**File**: `app/agents/editor.py`

**Purpose**: Format professional Markdown reports

**Decision-Making Process**:

1. **Structure Planning**:
   ```markdown
   # Triage Report: {repo}
   
   ## Executive Summary
   ## Clusters Overview
   ## Top Priority Issues
   ## Detailed Fix Plans
   ## Code Patches (if any)
   ## Citations
   ```

2. **Content Assembly**:
   - Aggregates all agent outputs
   - Orders by importance
   - Adds metadata (timestamp, processing time)

3. **Formatting Rules**:
   - Headers: ## for sections, ### for subsections
   - Tables for priorities (| # | Title | Score |)
   - Code blocks with language tags (```typescript)
   - Bullet lists for clusters and steps
   - Links to all GitHub URLs

4. **Confidence Indicators**:
   ```markdown
   🟢 High Confidence (>0.7)
   🟡 Medium Confidence (0.5-0.7)
   🔴 Low Confidence (<0.5)
   ```

5. **Citation Validation**:
   - Ensures all claims cite GitHub URLs
   - Verifies issue/PR numbers exist
   - Links to specific comments if referenced

**Key Prompt Elements**:
- "Create clean, professional Markdown"
- "Use headers, tables, code blocks"
- "Add confidence indicators"
- "Cite all GitHub URLs"

**Output**: Formatted Markdown report string

---

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- NVIDIA API key (for Nemotron access)
- Optional: GitHub personal access token (for higher rate limits)

### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd hell
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   **Dependencies**:
   - `fastapi` - Web framework
   - `uvicorn` - ASGI server
   - `httpx` - Async HTTP client
   - `pydantic` - Data validation
   - `python-dotenv` - Environment variables

3. **Set up environment variables**:

   Create a `.env` file in the project root:
   ```env
   # Required
   NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxx

   # Optional
   GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
   OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxx
   ```

4. **Verify setup**:
   ```bash
   python check_api.py
   ```

   Should output:
   ```
   ✅ NVIDIA API key configured
   ✅ API is accessible
   ```

---

## Usage Guide

### Starting the Server

**Method 1: Direct**:
```bash
python -m app.app
```

**Method 2: Uvicorn**:
```bash
uvicorn app.app:app --reload --host 0.0.0.0 --port 8000
```

**Method 3: Bash Script**:
```bash
chmod +x start.sh
./start.sh
```

Server starts at: `http://localhost:8000`

---

### Using the Web UI

1. **Open browser**: `http://localhost:8000`

2. **Enter repository**: 
   - Format: `owner/repo`
   - Example: `facebook/react`

3. **Set limit**: 
   - Recommended: 20-50 issues
   - Higher = more accurate but slower

4. **Click "Analyze Repository"**

5. **Wait for analysis** (30-90 seconds)
   - Progress updates appear in real-time
   - Shows which agent is running

6. **View results**:
   - Top 3 priority issues with scores
   - Click "Generate Code Fix" for any issue
   - View pseudocode explanation
   - Toggle to see full AI-generated code
   - Copy full Markdown report

---

### Using the REST API

**Health Check**:
```bash
curl http://localhost:8000/healthz
```

**Triage Endpoint**:
```bash
curl "http://localhost:8000/triage?repo=facebook/react&limit=30"
```

**Generate Code Patch**:
```bash
curl -X POST http://localhost:8000/generate-patch \
  -H "Content-Type: application/json" \
  -d '{
    "priority": {...},
    "plan": {...},
    "item": {...}
  }'
```

**Get Progress**:
```bash
curl http://localhost:8000/progress
```

**Debug Raw Data**:
```bash
curl "http://localhost:8000/debug/raw?repo=facebook/react&limit=10"
```

---

### Python Client Example

```python
import httpx
import asyncio

async def analyze_repo(repo: str, limit: int = 30):
    async with httpx.AsyncClient() as client:
        # Start triage
        response = await client.get(
            "http://localhost:8000/triage",
            params={"repo": repo, "limit": limit},
            timeout=120.0
        )
        data = response.json()
        
        # Print report
        print(data["report_markdown"])
        
        # Generate code for top issue
        if data["top_issues"]:
            top = data["top_issues"][0]
            plan = data["plans"][0]
            
            patch_response = await client.post(
                "http://localhost:8000/generate-patch",
                json={
                    "priority": top,
                    "plan": plan,
                    "item": {"number": top["number"], ...}
                }
            )
            patch = patch_response.json()
            print(f"\n🔧 Code Patch:\n{patch['patch']['pseudocode']}")

# Run
asyncio.run(analyze_repo("facebook/react", 30))
```

---

## Technical Details

### Caching Strategy

**Implementation**: `app/tools/cache.py`

```python
class TTLCache:
    def __init__(self, ttl_seconds=300):  # 5 minutes
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())
```

**Benefits**:
- Reduces GitHub API calls during agent retries
- Speeds up ReAct loops
- Prevents rate limit exhaustion

---

### Error Handling

**GitHub API Errors**:
```python
try:
    data = await github_client._get(url)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        return None  # Repository not found
    elif e.response.status_code == 403:
        raise RateLimitError()  # Rate limit exceeded
    else:
        raise
```

**LLM API Errors**:
```python
try:
    response = await llm_client.completion(messages)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        print("Model not accessible")
        # Suggest alternative model
    elif e.response.status_code == 401:
        print("Invalid API key")
    else:
        raise
```

**JSON Parsing Errors**:
```python
try:
    return json.loads(content)
except json.JSONDecodeError:
    # Try to extract from markdown code block
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
        return json.loads(content)
    else:
        # Return safe default
        return {"error": "Failed to parse JSON"}
```

---

### Performance Characteristics

**Typical Processing Times** (50 issues):
- Fetch from GitHub: 2-5 seconds
- Summarizer: 8-12 seconds
- Labeler: 6-10 seconds
- Prioritizer: 5-8 seconds
- Fix-Plan: 10-15 seconds
- Code Generator (on-demand): 8-12 seconds
- Editor: 5-8 seconds
- **Total**: 40-70 seconds

**Factors Affecting Speed**:
- Number of issues analyzed
- ReAct loop iterations (0-2 per agent)
- GitHub API response times
- LLM API latency
- Network conditions

**Optimization Tips**:
- Use GitHub token for faster API access
- Reduce limit for faster analysis
- Enable caching (default: ON)
- Use Nano 9B model (faster than 70B)

---

### Rate Limits

**GitHub API**:
- Without token: 60 requests/hour
- With token: 5,000 requests/hour
- Cache TTL: 5 minutes

**NVIDIA NIM API**:
- Varies by plan
- Free tier: ~100 requests/day
- Paid tier: Higher limits

**Recommendations**:
- Use GitHub token for production
- Monitor rate limit headers
- Implement retry with exponential backoff
- Cache GitHub data when possible

---

### Security Considerations

1. **API Keys**:
   - Never commit `.env` to git
   - Use environment variables only
   - Rotate keys periodically

2. **Input Validation**:
   - Repository name validated with regex
   - Limit parameter clamped (1-100)
   - All user input sanitized

3. **Code Generation**:
   - Review all AI-generated code before deploying
   - Test thoroughly in isolated environment
   - Never execute AI-generated code directly

4. **CORS**:
   - Currently allows all origins (dev mode)
   - Restrict in production:
     ```python
     allow_origins=["https://yourdomain.com"]
     ```

---

### Testing

**Manual Testing**:
```bash
# Test API health
curl http://localhost:8000/healthz

# Test with small repo
curl "http://localhost:8000/triage?repo=torvalds/linux&limit=10"

# Test debug endpoint
curl "http://localhost:8000/debug/raw?repo=facebook/react&limit=5"
```

**Recommended Test Repositories**:
- `facebook/react` - Large, active
- `vercel/next.js` - Modern stack
- `microsoft/vscode` - Diverse issues
- `tensorflow/tensorflow` - Technical depth

Start with `limit=20` for faster iteration.

---

### Troubleshooting

**Issue**: "NVIDIA_API_KEY is required"
- **Solution**: Export key or add to `.env`
  ```bash
  export NVIDIA_API_KEY="nvapi-xxxxx"
  ```

**Issue**: GitHub rate limit exceeded
- **Solution**: Add GitHub token or reduce limit
  ```bash
  export GITHUB_TOKEN="ghp-xxxxx"
  ```

**Issue**: LLM returns raw code instead of JSON
- **Solution**: Already handled with fallback parsing in `code_generator.py`

**Issue**: Analysis takes too long
- **Solution**: Reduce limit to 20-30 issues

**Issue**: Model not accessible (404)
- **Solution**: Use OpenRouter fallback
  1. Rename `llm_openrouter.py` to `llm.py`
  2. Set `OPENROUTER_API_KEY`

---

### Extending the System

**Adding a New Agent**:

1. Create `app/agents/new_agent.py`:
   ```python
   AGENT_PROMPT = """Your agent's system prompt"""
   
   async def new_agent_function(input_data, llm_client):
       messages = [
           {"role": "system", "content": AGENT_PROMPT},
           {"role": "user", "content": f"Process: {input_data}"}
       ]
       response = await llm_client.completion_json(messages)
       return process_response(response)
   ```

2. Update `app/router.py`:
   ```python
   from app.agents.new_agent import new_agent_function
   
   # In triage_repository():
   result = await new_agent_function(data, llm_client)
   ```

3. Update schemas if needed in `app/schemas/outputs.py`

**Adding a New Endpoint**:

1. In `app/app.py`:
   ```python
   @app.get("/new-endpoint")
   async def new_endpoint(param: str = Query(...)):
       result = await process(param)
       return {"result": result}
   ```

---

### Project Highlights

**What Makes This Special**:

✅ **Multi-Agent Architecture**: 6 specialized agents with clear responsibilities  
✅ **ReAct Pattern**: Agents fetch additional context when uncertain  
✅ **Interactive Code Generation**: User chooses which issues to fix  
✅ **Production-Ready**: Full API, web UI, error handling, caching  
✅ **Real-World Application**: Solves actual pain point for dev teams  
✅ **NVIDIA Nemotron**: Leverages Nano 9B for efficient reasoning  

---

### Future Enhancements

**Potential Improvements**:

1. **Parallel Agent Execution**: Run Summarizer + Labeler in parallel
2. **GitHub Integration**: Auto-apply labels and create PRs
3. **Multi-Repo Support**: Analyze multiple repos at once
4. **Historical Tracking**: Track priority changes over time
5. **Custom Scoring**: User-defined priority formulas
6. **Code Validation**: Syntax check before returning patches
7. **Testing Agent**: Generate unit tests for code patches
8. **Deployment Agent**: Create deployment plans and rollback strategies

---

## Credits

**Built by**: [Your Team Name]  
**For**: NVIDIA Nemotron Prize Track  
**Powered by**: NVIDIA Nemotron Nano 9B v2  
**Framework**: FastAPI + Python  
**APIs**: GitHub REST API, NVIDIA NIM API  

---

## License

MIT License - See LICENSE file for details

---

## Support

For questions or issues:
- Check troubleshooting section above
- Review error logs in console
- Test with smaller limits first
- Verify API keys are valid

---

**Built with ❤️ using NVIDIA Nemotron**
