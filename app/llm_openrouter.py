"""
Alternative: NVIDIA Nemotron via OpenRouter
Use this if your NVIDIA API key doesn't have Nemotron access
"""
import httpx
import json
import os
from typing import List, Dict, Optional, Any


# OpenRouter endpoint (has Nemotron models)
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"  # Available on OpenRouter


class LLMClient:
    """Client for OpenRouter (Nemotron access)"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Try OpenRouter key first, fall back to NVIDIA key
        self.api_key = os.getenv("OPENROUTER_API_KEY") or api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY or NVIDIA_API_KEY is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/gh-triage-lite",  # Required by OpenRouter
            "X-Title": "GH Triage Lite"  # Optional but good practice
        }
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send a chat completion request to OpenRouter"""
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        if response_format:
            payload["response_format"] = response_format
        
        try:
            response = await self.client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            print(f"HTTP error: {e.response.status_code}")
            print(f"Response: {error_detail}")
            
            if e.response.status_code == 401:
                print("\n⚠️  Get OpenRouter API key at: https://openrouter.ai/keys")
            
            raise
        except Exception as e:
            print(f"Error calling OpenRouter: {e}")
            raise
    
    async def completion_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Request a JSON response"""
        result = await self.completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        content = result["choices"][0]["message"]["content"]
        
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Content: {content}")
            return {"error": "Failed to parse JSON", "raw": content}
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global client instance
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client"""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client

