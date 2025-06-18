from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

OLLAMA_API_URL = "http://localhost:11434/v1/chat/completions"
OLLAMA_MODEL = "llama3"  # or another model you have installed in Ollama

class AnswerRequest(BaseModel):
    query: str
    data_preview: str  # Output from the sandbox (e.g., df.head() or column names)

class AnswerResponse(BaseModel):
    answer: str = None
    can_answer: bool = False

async def call_ollama(query: str, data_preview: str) -> str:
    prompt = (
        "You are a world-class data analysis expert.\n"
        "You are given the raw output from a Pandas operation in Python, and a user's question.\n"
        "If the output is a single value (like a string, number, or one-line answer), respond directly and naturally, as if you are an expert analyst giving a clear answer.\n"
        "If the output is a DataFrame/table, summary, or error, provide a concise, user-friendly summary and answer the user's question as best as possible.\n"
        "Do NOT repeat the raw output verbatim or explain your reasoning step-by-step unless the user asks for it.\n"
        "Be as clear, direct, and helpful as possible.\n"
        "If the output is an error, explain the problem and suggest a next step.\n"
        "---\n"
        f"Raw Pandas Output:\n{data_preview}\n"
        f"User's Question:\n{query}\n"
        "---\n"
        "Your answer (as a data analysis expert):"
    )
    data = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(OLLAMA_API_URL, json=data)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Ollama API error: {response.text}")
        result = response.json()
        try:
            answer = result["choices"][0]["message"]["content"].strip()
            return answer
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to parse LLM response.")

@router.post("/answer", response_model=AnswerResponse)
async def generate_answer(request: AnswerRequest):
    """Generate a user-friendly answer based on the data preview and user query using Ollama LLM."""
    answer = await call_ollama(request.query, request.data_preview)
    # Heuristic: If the LLM says the answer is not obvious, or not in the preview, set can_answer to False
    lower_answer = answer.lower()
    fallback_phrases = [
        "not obvious", "not shown", "not available", "cannot determine", "not present", "not enough information",
        "cannot answer", "need to look up", "would need to", "need to run code", "need to check", "need to execute",
        "need to use pandas", "need to use code", "need to see the data", "not enough data", "not enough context",
        "not in the preview", "not in preview", "not in the data preview", "not in data preview", "not in the provided preview",
        "not in provided preview", "not in the provided data", "not in provided data", "not in the provided output",
        "not in provided output", "not in the output", "not in output", "not in the shown data", "not in shown data"
    ]
    if any(phrase in lower_answer for phrase in fallback_phrases):
        return AnswerResponse(answer=answer, can_answer=False)
    return AnswerResponse(answer=answer, can_answer=True)