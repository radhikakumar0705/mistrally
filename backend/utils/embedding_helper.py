import os
import requests
import numpy as np

# Example Mistral endpoint (adjust model name as needed)
MISTRAL_API_URL = "https://api.mistral.ai/v1/embeddings"
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

def generate_embedding(text: str):
    """Generate an embedding vector from Mistral API."""
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-embed",  # replace with actual model name
        "input": text
    }

    response = requests.post(MISTRAL_API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Mistral API Error: {response.text}")

    data = response.json()
    return np.array(data["data"][0]["embedding"], dtype=float)

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
