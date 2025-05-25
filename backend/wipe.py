import os
from qdrant_client import QdrantClient

def reset_qdrant_collection(collection_name="pdf_chunks"):
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    if client.collection_exists(collection_name=collection_name):
        client.delete_collection(collection_name=collection_name)
        print(f"Collection '{collection_name}' deleted.")
    else:
        print(f"Collection '{collection_name}' does not exist.")

reset_qdrant_collection() 