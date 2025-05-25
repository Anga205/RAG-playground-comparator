from typing import Any
import google.generativeai as genai

def get_gemini_model(gemini_api_key: str, model_name: str = "gemini-1.5-flash-latest") -> Any:
    """
    Initialize and return a Gemini GenerativeModel instance.

    Args:
        gemini_api_key: Gemini API key.
        model_name: Gemini model name.

    Returns:
        Gemini GenerativeModel instance.
    """
    genai.configure(api_key=gemini_api_key)
    return genai.GenerativeModel(model_name)

async def gemini_generate_content(
    model: Any, 
    prompt: str
) -> str:
    """
    Generate content from Gemini model asynchronously.

    Args:
        model: Gemini GenerativeModel instance.
        prompt: Prompt string.

    Returns:
        Generated text response.
    """
    response = await model.generate_content_async(prompt)
    return response.text.strip()