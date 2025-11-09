#!/usr/bin/env python3
"""
Quick script to check NVIDIA API connectivity and available models
"""
import os
import sys

# Set API key (updated with new one from build.nvidia.com)
os.environ["NVIDIA_API_KEY"] = "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"

print("=" * 60)
print("NVIDIA API Connectivity Check")
print("=" * 60)

try:
    import httpx
    import asyncio
    
    api_key = os.getenv("NVIDIA_API_KEY")
    
    print(f"\n✓ API Key: {api_key[:15]}..." + "*" * 20)
    
    async def test_models():
        # Try different Nemotron model names (your API key has Nemotron Nano!)
        models_to_try = [
            # Nemotron models available with your API key
            "nvidia/nvidia-nemotron-nano-9b-v2",  # Better for reasoning tasks!
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "nvidia/nemotron-4-340b-instruct",
            "nvidia/llama-3_1-nemotron-70b-instruct",  # underscore variant
            # Fallback options (if Nemotron doesn't work)
            "meta/llama-3.1-70b-instruct", 
        ]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("\nTrying different models...\n")
            
            for model in models_to_try:
                print(f"Testing: {model}...")
                try:
                    response = await client.post(
                        "https://integrate.api.nvidia.com/v1/chat/completions",
                        headers=headers,
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": "Hi"}],
                            "max_tokens": 5,
                            "temperature": 0.5
                        }
                    )
                    
                    if response.status_code == 200:
                        print(f"  ✅ SUCCESS! Model '{model}' works!")
                        print(f"  Response: {response.json()}")
                        return model
                    else:
                        print(f"  ❌ Status {response.status_code}: {response.text[:100]}")
                        
                except Exception as e:
                    print(f"  ❌ Error: {str(e)[:100]}")
                
                print()
            
            print("❌ None of the models worked. Check:")
            print("   1. Your API key is valid")
            print("   2. You have access to models at https://build.nvidia.com")
            print("   3. Your internet connection")
            return None
    
    result = asyncio.run(test_models())
    
    if result:
        print("\n" + "=" * 60)
        print(f"✅ Use this model in app/llm.py:")
        print(f'   MODEL = "{result}"')
        print("=" * 60)
        sys.exit(0)
    else:
        sys.exit(1)
        
except ImportError as e:
    print(f"\n❌ Missing dependency: {e}")
    print("Run: pip install httpx")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)

