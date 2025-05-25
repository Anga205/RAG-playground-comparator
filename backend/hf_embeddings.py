from typing import List
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings

def get_hf_embeddings(
    texts: List[str], 
    hf_token: str, 
    model_name: str = "jinaai/jina-embeddings-v2-base-en"
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using Hugging Face Inference API.

    Args:
        texts: List of strings to embed.
        hf_token: Hugging Face API token.
        model_name: Model to use for embeddings.

    Returns:
        List of embedding vectors (one per input text).
    """
    embeddings_model = HuggingFaceInferenceAPIEmbeddings(
        api_key=hf_token, model_name=model_name
    )
    output = embeddings_model.embed_documents(texts)
    return output