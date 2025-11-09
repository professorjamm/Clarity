"""
NVIDIA NIM LLM Client for Nemotron
"""
import httpx
import json
import os
from typing import List, Dict, Optional, Any


# NVIDIA API Catalog endpoint
NVIDIA_BASE = "https://integrate.api.nvidia.com/v1"
# Nemotron models to try (in priority order)
MODEL = "nvidia/nvidia-nemotron-nano-9b-v2"  # Better for reasoning tasks!


class LLMClient:
    """Client for NVIDIA NIM API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
        """
        Send a chat completion request to NVIDIA NIM
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool schemas for function calling
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            response_format: Optional format spec (e.g., {"type": "json_object"})
        
        Returns:
            API response dict
        """
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95,
            "stream": False,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            # Reasoning parameters for Nemotron Nano 9B
            "extra_body": {
                "min_thinking_tokens": 1024,
                "max_thinking_tokens": 2048
            }
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        if response_format:
            payload["response_format"] = response_format
        
        try:
            response = await self.client.post(
                f"{NVIDIA_BASE}/chat/completions",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            print(f"HTTP error: {e.response.status_code}")
            print(f"Response: {error_detail}")
            
            # Provide helpful error messages
            if e.response.status_code == 404:
                print(f"\n⚠️  Model '{MODEL}' not found or not accessible.")
                print("Your API key might not have access to this model.")
                print("Try these solutions:")
                print("1. Check available models at: https://build.nvidia.com/explore/discover")
                print("2. Verify your API key has access to LLM models")
                print(f"3. Try a different model by editing app/llm.py (line 12)")
            elif e.response.status_code == 401:
                print("\n⚠️  Authentication failed. Check your NVIDIA_API_KEY")
            
            raise
        except Exception as e:
            print(f"Error calling NVIDIA API: {e}")
            raise
    
    async def completion_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Request a JSON response from the LLM
        """
        result = await self.completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Extract content from response
        content = result["choices"][0]["message"]["content"]
        original_content = content  # Keep for debugging
        
        # Try to parse JSON from the response
        try:
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Handle case where content starts with language identifier (e.g., "typescript\n// code...")
            # This happens when LLM returns code without JSON wrapper
            if content and not content.strip().startswith('{'):
                # Check if it looks like code with a language prefix
                lines = content.strip().split('\n', 1)
                if len(lines) > 1 and lines[0] in ['typescript', 'javascript', 'python', 'java', 'go', 'rust', 'c', 'cpp']:
                    # This is raw code, not JSON - return it in error format
                    print(f"⚠️ LLM returned raw code instead of JSON (language: {lines[0]})")
                    return {"error": "LLM returned raw code instead of JSON", "raw": original_content}
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            print(f"Content: {content[:200]}...")  # Only print first 200 chars
            # Return a safe default
            return {"error": "Failed to parse JSON", "raw": original_content}
    
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

