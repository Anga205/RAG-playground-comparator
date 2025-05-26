from transformers import AutoTokenizer, AutoModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
import torch
import torch.nn.functional as F
from db_utils import search_similar_chunks
import json
from ai_utils import query_gemini

# Load the tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("jinaai/jina-embeddings-v2-base-en")
model = AutoModel.from_pretrained("jinaai/jina-embeddings-v2-base-en")
model.eval()

def split_text_into_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_text(text)

def get_vector_embeddings(chunks):
    embeddings = []
    for text in chunks:
        # Tokenize the input text
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        
        # Forward pass through the model
        with torch.no_grad():
            outputs = model(**inputs)
        
        # Mean pooling
        last_hidden_state = outputs.last_hidden_state
        attention_mask = inputs['attention_mask']
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        embedding = sum_embeddings / sum_mask

        # Normalize the embedding
        embedding = F.normalize(embedding, p=2, dim=1)

        embeddings.append(embedding.squeeze().tolist())
    return embeddings

def vanilla_get_chunks(query_text:str, top_k:int = 3) -> list[str]:
    query_inputs = tokenizer(query_text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**query_inputs)
    last_hidden_state = outputs.last_hidden_state
    attention_mask = query_inputs['attention_mask']
    mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    sum_embeddings = torch.sum(last_hidden_state * mask_expanded, 1)
    sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
    query_embedding = (sum_embeddings / sum_mask)
    query_embedding = F.normalize(query_embedding, p=2, dim=1).squeeze().tolist()
    similar_chunks = search_similar_chunks(query_embedding, top_k=top_k)
    return similar_chunks

def extract_query_insights(query_text: str, max_retries: int = 3) -> dict:
    prompt = f"""You are an intelligent assistant that transforms natural language queries into structured information to improve search results.\n\nGiven the question: "{query_text}"\n\nReturn a JSON with the following fields:\n- "keywords": important terms to use in search\n- "topics": broader themes\n- "intent": is the user asking for definition, cause, impact, solution, etc.?\n\nRespond with only the JSON object.\n"""
    for attempt in range(max_retries):
        response = query_gemini(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            if attempt == max_retries - 1:
                return {"keywords": [], "topics": [], "intent": "unknown"}
    return {"keywords": [], "topics": [], "intent": "unknown"}

def get_self_query_embedding(query_text: str) -> list[float]:
    """Use Gemini to reformulate the query and compute its embedding."""
    insights = extract_query_insights(query_text)
    enriched_query = f"{query_text}. Keywords: {', '.join(insights['keywords'])}. Intent: {insights['intent']}. Topics: {', '.join(insights['topics'])}"
    
    inputs = tokenizer(enriched_query, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)

    last_hidden_state = outputs.last_hidden_state
    attention_mask = inputs['attention_mask']
    mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    sum_embeddings = torch.sum(last_hidden_state * mask_expanded, 1)
    sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
    query_embedding = F.normalize(sum_embeddings / sum_mask, p=2, dim=1)
    return query_embedding.squeeze().tolist()