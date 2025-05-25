# Test your Hugging Face Inference API token with Jina Embeddings
import requests
import os

HF_TOKEN = os.getenv("HF_TOKEN") or "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"  # Replace if not using env

API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/jinaai/jina-embeddings-v2-base-en"
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}
data = {
    "inputs": ["This is a test sentence for embedding."]
}

response = requests.post(API_URL, headers=headers, json=data)

print("Status code:", response.status_code)
try:
    result = response.json()
    print("JSON response:", result)
    if isinstance(result, list):
        print("✅ Token works! Received embeddings.")
    else:
        print("⚠️ Token accepted, but unexpected response:", result)
except Exception as e:
    print("❌ Failed to decode JSON. Response text:")
    print(response.text)
    print("Error:", e)