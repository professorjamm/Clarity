"""
GitHub REST API client
"""
import httpx
from typing import List, Dict, Any, Optional
from app.schemas.outputs import FetchedItem
from app.tools.cache import get_cache


GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """Client for GitHub REST API"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GH-Triage-Lite"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        
        self.client = httpx.AsyncClient(timeout=30.0)
        self.cache = get_cache()
    
    async def _get(self, url: str, use_cache: bool = True) -> Any:
        """Make a GET request with optional caching"""
        if use_cache:
            cached = self.cache.get(url)
            if cached is not None:
                return cached
        
        try:
            response = await self.client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if use_cache:
                self.cache.set(url, data)
            
            return data
        except httpx.HTTPStatusError as e:
            print(f"GitHub API error: {e.response.status_code} for {url}")
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            print(f"Error fetching from GitHub: {e}")
            raise
    
    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 50,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        List issues for a repository (includes PRs)
        https://docs.github.com/en/rest/issues/issues#list-repository-issues
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
        params = f"?state={state}&per_page={per_page}&page={page}&sort=updated&direction=desc"
        full_url = url + params
        
        result = await self._get(full_url)
        return result if result else []
    
    async def list_pulls(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List pull requests for a repository
        https://docs.github.com/en/rest/pulls/pulls#list-pull-requests
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
        params = f"?state={state}&per_page={per_page}&sort=updated&direction=desc"
        full_url = url + params
        
        result = await self._get(full_url)
        return result if result else []
    
    async def list_issue_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int
    ) -> List[Dict[str, Any]]:
        """
        List comments for an issue
        https://docs.github.com/en/rest/issues/comments#list-issue-comments
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        result = await self._get(url)
        return result if result else []
    
    async def list_pr_reviews(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """
        List reviews for a pull request
        https://docs.github.com/en/rest/pulls/reviews#list-reviews-for-a-pull-request
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        result = await self._get(url)
        return result if result else []
    
    async def fetch_all_items(
        self,
        owner: str,
        repo: str,
        limit: int = 50,
        include_prs: bool = True,
        include_issues: bool = True
    ) -> List[FetchedItem]:
        """
        Fetch all issues and PRs, convert to FetchedItem schema
        """
        # GitHub issues endpoint returns both issues and PRs
        raw_items = await self.list_issues(owner, repo, per_page=limit)
        
        fetched_items = []
        for item in raw_items[:limit]:
            # Determine if it's a PR or issue
            is_pr = "pull_request" in item
            
            # Filter based on preferences
            if is_pr and not include_prs:
                continue
            if not is_pr and not include_issues:
                continue
            
            # Extract labels
            labels = [label["name"] for label in item.get("labels", [])]
            
            # Build FetchedItem
            fetched_item = FetchedItem(
                type="pr" if is_pr else "issue",
                number=item["number"],
                title=item["title"],
                body=item.get("body", ""),
                labels=labels,
                state=item["state"],
                comments=item.get("comments", 0),
                updated_at=item["updated_at"],
                html_url=item["html_url"],
                extra={}
            )
            
            fetched_items.append(fetched_item)
        
        return fetched_items
    
    async def batch_fetch_comments(
        self,
        owner: str,
        repo: str,
        issue_numbers: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Fetch comments for multiple issues
        Returns dict mapping issue_number -> comments
        """
        results = {}
        for number in issue_numbers:
            comments = await self.list_issue_comments(owner, repo, number)
            results[number] = comments
        return results
    
    async def batch_fetch_reviews(
        self,
        owner: str,
        repo: str,
        pr_numbers: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Fetch reviews for multiple PRs
        Returns dict mapping pr_number -> reviews
        """
        results = {}
        for number in pr_numbers:
            reviews = await self.list_pr_reviews(owner, repo, number)
            results[number] = reviews
        return results
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

