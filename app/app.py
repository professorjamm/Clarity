"""
Clarity - FastAPI Server
Multi-agent GitHub issue triage system with automated code generation
"""
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv
import os

from app.schemas.inputs import TriageRequest
from app.schemas.outputs import TriageResponse, CodePatch, FetchedItem, PriorityEntry, FixPlan
from app.router import triage_repository, parse_repo, get_progress
from app.tools.github import GitHubClient
from app.llm import get_llm_client
from app.agents.code_generator import generate_code_patch

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Clarity",
    description="Multi-agent GitHub issue triage with AI-powered code generation",
    version="2.0.0"
)

# CORS middleware for UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "clarity",
        "nvidia_api_configured": bool(os.getenv("NVIDIA_API_KEY"))
    }


@app.get("/progress")
async def progress_endpoint():
    """
    Get current progress of the analysis
    
    Returns progress log with messages from the current triage session
    """
    return get_progress()


@app.get("/triage", response_model=TriageResponse)
async def triage_endpoint(
    repo: str = Query(..., description="Repository in format 'owner/name'"),
    limit: int = Query(50, ge=1, le=100, description="Max issues to fetch"),
    include_prs: bool = Query(True, description="Include pull requests"),
    include_issues: bool = Query(True, description="Include issues")
):
    """
    Main triage endpoint - analyzes a GitHub repository
    
    Example: /triage?repo=vercel/next.js&limit=30
    """
    try:
        request = TriageRequest(
            repo=repo,
            limit=limit,
            include_prs=include_prs,
            include_issues=include_issues
        )
        
        result = await triage_repository(request)
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing triage: {str(e)}")


@app.get("/debug/raw")
async def debug_raw_items(
    repo: str = Query(..., description="Repository in format 'owner/name'"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Debug endpoint - returns raw fetched items
    
    Example: /debug/raw?repo=facebook/react&limit=10
    """
    try:
        owner, repo_name = parse_repo(repo)
        
        github_client = GitHubClient()
        try:
            items = await github_client.fetch_all_items(
                owner=owner,
                repo=repo_name,
                limit=limit
            )
            return {
                "repo": repo,
                "count": len(items),
                "items": [item.model_dump() for item in items]
            }
        finally:
            await github_client.close()
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching items: {str(e)}")


@app.post("/generate-patch")
async def generate_patch_endpoint(issue_data: dict = Body(...)):
    """
    On-demand code patch generation for a specific issue
    
    Expects issue_data with: priority, plan, and item details
    """
    try:
        # Parse the issue data
        priority = PriorityEntry(**issue_data.get("priority"))
        plan = FixPlan(**issue_data.get("plan"))
        item = FetchedItem(**issue_data.get("item"))
        
        # Get LLM client
        llm_client = get_llm_client()
        
        # Generate patch
        print(f"💻 Generating code patch for issue #{priority.number}...")
        patch_data = await generate_code_patch(
            top_issue=priority,
            fix_plan=plan,
            item=item,
            llm_client=llm_client
        )
        
        if not patch_data:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to generate code patch"}
            )
        
        # Create CodePatch object
        code_patch = CodePatch(**patch_data)
        print(f"✅ Generated patch with confidence: {code_patch.confidence:.2f}")
        
        return {
            "success": True,
            "patch": code_patch.model_dump()
        }
    
    except Exception as e:
        print(f"❌ Error generating patch: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Clarity - Dark minimalist UI for issue triage
    """
    html_content = r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Clarity - AI-Powered Issue Triage</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            :root {
                --bg-primary: #0a0a0a;
                --bg-secondary: #141414;
                --bg-tertiary: #1a1a1a;
                --accent: #00d4ff;
                --accent-hover: #00b8e6;
                --text-primary: #ffffff;
                --text-secondary: #a0a0a0;
                --text-muted: #6b6b6b;
                --border: #2a2a2a;
                --success: #00ff88;
                --warning: #ffaa00;
                --error: #ff4444;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
                background: var(--bg-primary);
                color: var(--text-primary);
                line-height: 1.6;
                min-height: 100vh;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            
            /* Header */
            .header {
                text-align: center;
                margin-bottom: 60px;
            }
            
            .logo {
                font-size: 3.5em;
                font-weight: 700;
                letter-spacing: -0.03em;
                background: linear-gradient(135deg, var(--accent) 0%, #00ff88 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 10px;
            }
            
            .tagline {
                font-size: 1.1em;
                color: var(--text-secondary);
                font-weight: 400;
            }
            
            /* Cards */
            .card {
                background: var(--bg-secondary);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 24px;
                transition: border-color 0.3s;
            }
            
            .card:hover {
                border-color: #3a3a3a;
            }
            
            /* Form */
            .form-grid {
                display: grid;
                grid-template-columns: 1fr 200px;
                gap: 16px;
                margin-bottom: 16px;
            }
            
            .form-group {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .form-group label {
                font-size: 0.85em;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                color: var(--text-muted);
                font-weight: 600;
            }
            
            .form-group input {
                background: var(--bg-primary);
                border: 1px solid var(--border);
                color: var(--text-primary);
                padding: 14px 16px;
                border-radius: 8px;
                font-size: 15px;
                transition: all 0.2s;
            }
            
            .form-group input:focus {
                outline: none;
                border-color: var(--accent);
                box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.1);
            }
            
            /* Buttons */
            .btn {
                background: var(--accent);
                color: var(--bg-primary);
                border: none;
                padding: 14px 32px;
                font-size: 15px;
                font-weight: 600;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.2s;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            .btn:hover {
                background: var(--accent-hover);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
            }
            
            .btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }
            
            .btn-secondary {
                background: transparent;
                border: 1px solid var(--border);
                color: var(--text-primary);
                padding: 10px 20px;
                font-size: 14px;
            }
            
            .btn-secondary:hover {
                background: var(--bg-tertiary);
                border-color: var(--accent);
                box-shadow: none;
            }
            
            .btn-generate {
                background: linear-gradient(135deg, var(--accent) 0%, var(--success) 100%);
                padding: 12px 24px;
                font-size: 14px;
            }
            
            /* Loading */
            .loading {
                display: none;
                text-align: center;
                padding: 60px 20px;
            }
            
            .spinner {
                width: 50px;
                height: 50px;
                border: 3px solid var(--border);
                border-top-color: var(--accent);
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin: 0 auto 20px;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            .loading-text {
                color: var(--text-secondary);
                font-size: 14px;
            }
            
            .progress-message {
                color: var(--text-secondary);
                font-size: 13px;
                padding: 8px 16px;
                margin: 4px 0;
                background: var(--bg-tertiary);
                border-left: 3px solid var(--accent);
                border-radius: 4px;
                text-align: left;
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                animation: slideIn 0.3s ease-out;
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            /* Results */
            #results {
                display: none;
            }
            
            .section-title {
                font-size: 1.8em;
                font-weight: 700;
                margin-bottom: 24px;
                color: var(--text-primary);
            }
            
            /* Issue Cards */
            .issue-card {
                background: var(--bg-tertiary);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 16px;
                transition: all 0.2s;
            }
            
            .issue-card:hover {
                border-color: var(--accent);
                transform: translateX(4px);
            }
            
            .issue-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 16px;
            }
            
            .issue-number {
                font-size: 0.9em;
                color: var(--accent);
                font-weight: 600;
            }
            
            .issue-title {
                font-size: 1.2em;
                font-weight: 600;
                margin: 8px 0;
                color: var(--text-primary);
            }
            
            .score-badge {
                background: linear-gradient(135deg, var(--accent) 0%, var(--success) 100%);
                color: var(--bg-primary);
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: 700;
                font-size: 1.1em;
            }
            
            .metrics {
                display: flex;
                gap: 24px;
                margin: 12px 0;
                font-size: 0.9em;
            }
            
            .metric {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            
            .metric-label {
                color: var(--text-muted);
            }
            
            .metric-value {
                color: var(--text-primary);
                font-weight: 600;
            }
            
            /* Code Patches */
            .patch-container {
                background: var(--bg-primary);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 20px;
                margin-top: 16px;
            }
            
            .patch-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
            }
            
            .confidence-badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 0.85em;
                font-weight: 600;
            }
            
            .confidence-high { background: rgba(0, 255, 136, 0.2); color: var(--success); }
            .confidence-medium { background: rgba(255, 170, 0, 0.2); color: var(--warning); }
            .confidence-low { background: rgba(255, 68, 68, 0.2); color: var(--error); }
            
            .patch-explanation {
                color: var(--text-secondary);
                margin-bottom: 16px;
                line-height: 1.6;
            }
            
            .code-block {
                background: #000000;
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 16px;
                overflow-x: auto;
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.6;
                color: #e6e6e6;
            }
            
            .code-block pre {
                margin: 0;
            }
            
            .file-path {
                font-family: monospace;
                color: var(--accent);
                font-size: 0.9em;
                margin-bottom: 12px;
            }
            
            /* Markdown Content */
            .markdown-content {
                color: var(--text-secondary);
                line-height: 1.8;
            }
            
            .markdown-content h2 {
                color: var(--text-primary);
                margin-top: 32px;
                margin-bottom: 16px;
                font-size: 1.5em;
            }
            
            .markdown-content h3 {
                color: var(--text-primary);
                margin-top: 24px;
                margin-bottom: 12px;
                font-size: 1.2em;
            }
            
            .markdown-content a {
                color: var(--accent);
                text-decoration: none;
            }
            
            .markdown-content a:hover {
                text-decoration: underline;
            }
            
            /* Utility */
            .hidden { display: none !important; }
            
            .text-muted {
                color: var(--text-muted);
                font-size: 0.9em;
            }
            
            /* Responsive */
            @media (max-width: 768px) {
                .form-grid {
                    grid-template-columns: 1fr;
                }
                
                .logo {
                    font-size: 2.5em;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 class="logo">Clarity</h1>
                <p class="tagline">AI-Powered Issue Triage with Automated Code Generation</p>
            </div>
            
            <div class="card" id="input-card">
                <form id="triageForm">
                    <div class="form-grid">
                        <div class="form-group">
                            <label for="repo">Repository</label>
                            <input type="text" id="repo" name="repo" placeholder="owner/repository" required>
                        </div>
                        <div class="form-group">
                            <label for="limit">Issue Limit</label>
                            <input type="number" id="limit" name="limit" value="30" min="5" max="100" required>
                        </div>
                    </div>
                    <button type="submit" class="btn" id="submitBtn">Analyze Repository</button>
                </form>
                
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p class="loading-text">Analyzing repository with 6 AI agents...</p>
                    <p class="loading-text text-muted" style="margin-top: 8px;">This may take 30-90 seconds</p>
                    <div id="progress-log" style="margin-top: 24px; max-width: 600px; margin-left: auto; margin-right: auto;"></div>
                </div>
            </div>
            
            <div id="results">
                <div class="card">
                    <h2 class="section-title">Top Priority Issues</h2>
                    <p class="text-muted" style="margin-bottom: 24px;">Select an issue to generate an automated code fix</p>
                    <div id="issues-container"></div>
                </div>
                
                <div class="card" id="full-report-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                        <h2 class="section-title" style="margin: 0;">Complete Analysis Report</h2>
                        <button class="btn-secondary" onclick="copyMarkdown()">Copy Markdown</button>
                    </div>
                    <div id="markdown-output" class="markdown-content"></div>
                </div>
            </div>
        </div>
        
        <script>
            let triageData = null;
            let generatedPatches = new Map();
            let progressPollInterval = null;
            let lastProgressCount = 0;
            
            async function pollProgress() {
                try {
                    const response = await fetch('/progress');
                    const data = await response.json();
                    
                    if (data.log && data.log.length > lastProgressCount) {
                        const progressLog = document.getElementById('progress-log');
                        
                        // Add only new messages
                        for (let i = lastProgressCount; i < data.log.length; i++) {
                            const entry = data.log[i];
                            const messageDiv = document.createElement('div');
                            messageDiv.className = 'progress-message';
                            messageDiv.textContent = `${entry.emoji} ${entry.message}`;
                            progressLog.appendChild(messageDiv);
                        }
                        
                        lastProgressCount = data.log.length;
                    }
                } catch (error) {
                    console.error('Error polling progress:', error);
                }
            }
            
            function startProgressPolling() {
                lastProgressCount = 0;
                document.getElementById('progress-log').innerHTML = '';
                
                // Poll every 500ms
                progressPollInterval = setInterval(pollProgress, 500);
            }
            
            function stopProgressPolling() {
                if (progressPollInterval) {
                    clearInterval(progressPollInterval);
                    progressPollInterval = null;
                }
            }
            
            document.getElementById('triageForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const repo = document.getElementById('repo').value;
                const limit = document.getElementById('limit').value;
                
                // Show loading
                document.getElementById('triageForm').style.display = 'none';
                document.getElementById('loading').style.display = 'block';
                document.getElementById('results').style.display = 'none';
                
                // Start polling for progress updates
                startProgressPolling();
                
                try {
                    const response = await fetch(`/triage?repo=${encodeURIComponent(repo)}&limit=${limit}`);
                    const data = await response.json();
                    
                    // Stop polling
                    stopProgressPolling();
                    
                    if (!response.ok) {
                        throw new Error(data.detail || 'Error analyzing repository');
                    }
                    
                    triageData = data;
                    generatedPatches.clear();
                    
                    // Display issues
                    displayIssues(data.top_issues, data.plans, data.metadata);
                    
                    // Store markdown
                    window.markdownContent = data.report_markdown;
                    
                    // Convert markdown to basic HTML
                    const htmlContent = simpleMarkdownToHTML(data.report_markdown);
                    document.getElementById('markdown-output').innerHTML = htmlContent;
                    
                    // Show results
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('results').style.display = 'block';
                    
                } catch (error) {
                    stopProgressPolling();
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('triageForm').style.display = 'block';
                    alert('Error: ' + error.message);
                }
            });
            
            function displayIssues(priorities, plans, metadata) {
                const container = document.getElementById('issues-container');
                container.innerHTML = '';
                
                priorities.forEach((priority, idx) => {
                    const plan = plans[idx];
                    const issueCard = document.createElement('div');
                    issueCard.className = 'issue-card';
                    issueCard.id = `issue-${priority.number}`;
                    
                    issueCard.innerHTML = `
                        <div class="issue-header">
                            <div>
                                <div class="issue-number">Issue #${priority.number}</div>
                                <h3 class="issue-title">${escapeHtml(priority.title)}</h3>
                                <div class="metrics">
                                    <div class="metric">
                                        <span class="metric-label">Severity:</span>
                                        <span class="metric-value">${priority.severity}/5</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">Impact:</span>
                                        <span class="metric-value">${priority.impact}/5</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">Effort:</span>
                                        <span class="metric-value">${priority.effort}/5</span>
                                    </div>
                                </div>
                            </div>
                            <div class="score-badge">${priority.score.toFixed(0)}</div>
                        </div>
                        <p class="text-muted" style="margin-bottom: 16px;">${escapeHtml(priority.justification)}</p>
                        <button class="btn-generate" onclick="generatePatch(${priority.number}, ${idx})">
                            Generate Code Fix
                        </button>
                        <div id="patch-${priority.number}" class="hidden"></div>
                    `;
                    
                    container.appendChild(issueCard);
                });
            }
            
            async function generatePatch(issueNumber, idx) {
                // Check if already generated
                if (generatedPatches.has(issueNumber)) {
                    return;
                }
                
                const btn = event.target;
                btn.disabled = true;
                btn.textContent = 'Generating...';
                
                try {
                    // Find the issue data
                    const priority = triageData.top_issues[idx];
                    const plan = triageData.plans[idx];
                    const item = triageData.metadata.items_fetched ? 
                        await fetchIssueData(triageData.repo, issueNumber) : null;
                    
                    // Call generate-patch endpoint
                    const response = await fetch('/generate-patch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            priority: priority,
                            plan: plan,
                            item: item || { 
                                type: 'issue',
                                number: issueNumber,
                                title: priority.title,
                                body: priority.justification,
                                labels: [],
                                state: 'open',
                                comments: 0,
                                updated_at: new Date().toISOString(),
                                html_url: priority.links[0] || '',
                                extra: {}
                            }
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        generatedPatches.set(issueNumber, result.patch);
                        displayPatch(issueNumber, result.patch);
                        btn.textContent = '✓ Code Generated';
                        btn.style.background = 'var(--success)';
                    } else {
                        throw new Error(result.error || 'Failed to generate patch');
                    }
                    
                } catch (error) {
                    console.error('Error generating patch:', error);
                    btn.disabled = false;
                    btn.textContent = 'Generate Code Fix (Error - Retry)';
                    alert('Error generating patch: ' + error.message);
                }
            }
            
            function displayPatch(issueNumber, patch) {
                const container = document.getElementById(`patch-${issueNumber}`);
                container.classList.remove('hidden');
                
                let confidenceClass = 'confidence-low';
                let confidenceText = '🔴 Low';
                if (patch.confidence >= 0.7) {
                    confidenceClass = 'confidence-high';
                    confidenceText = '🟢 High';
                } else if (patch.confidence >= 0.5) {
                    confidenceClass = 'confidence-medium';
                    confidenceText = '🟡 Medium';
                }
                
                // Use pseudocode if available, otherwise fallback to patch_content
                const pseudocode = patch.pseudocode || patch.patch_content;
                const fullCode = patch.full_code;
                
                container.innerHTML = `
                    <div class="patch-container">
                        <div class="patch-header">
                            <h4 style="color: var(--text-primary);">Fix Guide (Pseudocode)</h4>
                            <span class="confidence-badge ${confidenceClass}">
                                Confidence: ${confidenceText} (${(patch.confidence * 100).toFixed(0)}%)
                            </span>
                        </div>
                        <div class="file-path">📄 ${escapeHtml(patch.file_path)}</div>
                        <p class="patch-explanation">${escapeHtml(patch.explanation)}</p>
                        ${patch.approach ? `<p class="text-muted" style="margin-bottom: 12px;"><strong>Approach:</strong> ${escapeHtml(patch.approach)}</p>` : ''}
                        <div class="code-block"><pre>${escapeHtml(pseudocode)}</pre></div>
                        ${fullCode ? `
                            <div style="margin-top: 16px;">
                                <button class="btn-secondary" onclick="toggleFullCode(${issueNumber})" id="toggle-btn-${issueNumber}">
                                    Show AI-Generated Code
                                </button>
                                <div id="full-code-${issueNumber}" class="hidden" style="margin-top: 12px;">
                                    <h4 style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 8px;">Full AI-Generated Implementation:</h4>
                                    <div class="code-block"><pre>${escapeHtml(fullCode)}</pre></div>
                                </div>
                            </div>
                        ` : ''}
                        ${patch.notes ? `<p class="text-muted" style="margin-top: 12px; font-size: 0.85em;"><em>${escapeHtml(patch.notes)}</em></p>` : ''}
                    </div>
                `;
            }
            
            function toggleFullCode(issueNumber) {
                const fullCodeDiv = document.getElementById(`full-code-${issueNumber}`);
                const toggleBtn = document.getElementById(`toggle-btn-${issueNumber}`);
                
                if (fullCodeDiv.classList.contains('hidden')) {
                    fullCodeDiv.classList.remove('hidden');
                    toggleBtn.textContent = 'Hide AI-Generated Code';
                } else {
                    fullCodeDiv.classList.add('hidden');
                    toggleBtn.textContent = 'Show AI-Generated Code';
                }
            }
            
            async function fetchIssueData(repo, issueNumber) {
                // Simplified - in real implementation, would fetch from GitHub
                return null;
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            function copyMarkdown() {
                if (!window.markdownContent) {
                    alert('No content to copy');
                    return;
                }
                
                navigator.clipboard.writeText(window.markdownContent).then(() => {
                    event.target.textContent = '✓ Copied!';
                    setTimeout(() => event.target.textContent = 'Copy Markdown', 2000);
                }).catch(err => {
                    console.error('Failed to copy:', err);
                    alert('Failed to copy: ' + err.message);
                });
            }
            
            function simpleMarkdownToHTML(markdown) {
                return markdown
                    .replace(/### (.*)/g, '<h3>$1</h3>')
                    .replace(/## (.*)/g, '<h2>$1</h2>')
                    .replace(/# (.*)/g, '<h1>$1</h1>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/- (.*)/g, '<li>$1</li>')
                    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
                    .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>')
                    .replace(/\n\n/g, '<br><br>');
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
