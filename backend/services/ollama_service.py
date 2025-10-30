import requests

# Local Ollama endpoint (Mistral)
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"

def query_mistral(prompt: str) -> str:
    """
    Send a prompt to the local Mistral model via Ollama REST API.
    """
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()

        data = response.json()
        return data.get("response", "").strip()

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Ollama request failed: {e}")
        return "Sorry, I had trouble connecting to the local model."
