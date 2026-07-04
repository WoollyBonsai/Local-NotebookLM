import requests
from litellm import completion
from app.config import settings

def auto_detect_model(api_base: str, default: str) -> str:
    if not api_base:
        return default
    try:
        url = f"{api_base}/api/tags"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            if models:
                return f"ollama/{models[0]['name']}"
    except Exception as e:
        print(f"Auto-detect failed for {api_base}: {e}")
    return default

def update_models():
    settings.LOCAL_MODEL = auto_detect_model(settings.LOCAL_LLM_ENDPOINT, "ollama/llama3.1")
    settings.CLOUD_MODEL = auto_detect_model(settings.CLOUD_LLM_ENDPOINT, "ollama/llama3.1")

def call_llm(prompt: str, max_tokens: int = 200, temperature: float = 0.7):
    # Try Cloud First
    if settings.CLOUD_LLM_ENDPOINT:
        try:
            return completion(
                model=settings.CLOUD_MODEL,
                api_base=settings.CLOUD_LLM_ENDPOINT,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
        except Exception as e:
            print(f"Cloud LLM Failed, falling back to Local: {e}")
            pass
            
    # Fallback to Local
    return completion(
        model=settings.LOCAL_MODEL,
        api_base=settings.LOCAL_LLM_ENDPOINT,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature
    )
