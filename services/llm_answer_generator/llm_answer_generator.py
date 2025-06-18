from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

OLLAMA_API_URL = "http://localhost:11434/v1/chat/completions"
OLLAMA_MODEL = "granite3.3:8b"  # or another model you have installed in Ollama

class AnswerRequest(BaseModel):
    query: str
    data_preview: str  # Output from the sandbox (e.g., df.head() or column names)
    columns: str = None  # Dataset columns (schema)
    code: str = None    # The code that was run

class AnswerResponse(BaseModel):
    answer: str = None
    can_answer: bool = False

async def call_ollama(query: str, data_preview: str, columns: str = None, code: str = None) -> str:
    prompt = '''You are a world-class data analysis expert specializing in interpreting and explaining data queries and results in clear, human-friendly language. You generate natural language answers based on:

1. The dataset schema (column names provided).
2. The Python Pandas code that was executed.
3. The resulting data (preview shown).
4. The user’s original question.

---

### General Behavior Guidelines:

1. **Understand User Intent (Chain-of-Thought Reasoning Required):**

   * Carefully read the user's question.
   * Determine if the user wants:

     * A minimum or maximum value?
     * The best or worst outcome?
     * A summary, count, mean, etc.?
   * Determine the meaning of terms like "best" or "worst" in context:

     * E.g., Higher AQI = worse air, lower error = better model, etc.

2. **Code and Output Verification:**

   * Understand what the provided code does.
   * Match the code result to the user's original question.
   * Use the actual `data_preview` to frame your answer correctly.

3. **Provide Clear, Direct, Human-Readable Answers:**

   * Your output must summarize the result simply and precisely.
   * Example: "The city with the worst air quality index is Talcher with an AQI of 2049, which is the highest in the dataset."

4. **Explain Reasoning When Needed (Internally Reason, Selectively Output):**

   * If the user's question could be misinterpreted (e.g., worst = min or max?), clarify in your own reasoning before generating the final answer.
   * But only output the final clean human-readable answer (not your reasoning).

5. **Handle Single-Row or Single-Value Outputs Gracefully:**

   * If the result is a single value, report it naturally (e.g., "The mean age is 36.4 years.").
   * If it's a list or summary, summarize meaningfully.

6. **If the result does not answer the user's question completely (e.g., wrong column, missing data), hint politely:**

   * "The result is based only on the available data for [columns]. Additional information may be needed for a complete answer."

7. **Avoid Raw Code, Numbers Without Context, or Overly Technical Jargon.**

   * Always explain what the result means in simple terms.

---

### Chain-of-Thought Reasoning (Internal, Mandatory):

1. What is the user's question asking?
2. What does the executed code do in Pandas?
3. What is the result preview showing?
4. Does the result answer the user’s question properly?
5. Generate a final sentence or two that clearly explains the result to the user.

---

### Example (Internal Reasoning Only, Not Output to User):

**User Question:** "Which city has the worst air quality index?"

**Executed Code:** `df.loc[df['AQI'].idxmax()]['city']`

**Result Preview:** `Talcher`

**Reasoning:**

* The code finds the city with the highest AQI.
* Higher AQI = worse air quality.
* The result "Talcher" matches the user’s request.

**Final Output to User:**
"The city with the worst air quality index is Talcher, as it has the highest AQI in the dataset."

---

### Important Output Rules:

* Output only the final clear human answer.
* Do NOT include reasoning, code, or data previews in the output.
* Do NOT use phrases like "According to the code…" or "As per the result…" — just state the insight confidently.
* Example Final Output:

  * "There is only one city in the dataset: Ahmedabad. Therefore, no comparison of air quality index across cities is possible."

---

### Summary:

* Deeply reason (internally).
* Output simple, human-friendly insights.
* Never show code or previews.
* Always reflect understanding of the data domain (e.g., higher AQI = worse air).
'''
    prompt += f"\n\nDataset columns: {columns}\n" if columns else ""
    prompt += f"\nExecuted code: {code}\n" if code else ""
    prompt += f"\nResult preview: {data_preview}\n"
    prompt += f"\nUser question: {query}\n"
    data = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    async with httpx.AsyncClient(timeout=120000000.0) as client:
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
    """Generate a user-friendly answer based on the data preview, user query, columns, and code using Ollama LLM."""
    answer = await call_ollama(request.query, request.data_preview, request.columns, request.code)
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
