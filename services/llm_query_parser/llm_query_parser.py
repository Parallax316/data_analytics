from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

OLLAMA_API_URL = "http://localhost:11434/v1/chat/completions"
OLLAMA_MODEL = "llama3"  # or another model you have installed in Ollama

class QueryRequest(BaseModel):
    query: str
    schema: str = None  # Optional: pass a string describing the dataframe schema

class QueryResponse(BaseModel):
    pandas_code: str

async def call_ollama(query: str, schema: str = None) -> str:
    prompt = (
        "You are an expert Python pandas code generator. "
        "Your job is to convert a user's natural language question about a pandas DataFrame into a single, correct, executable pandas code snippet. "
        "ALWAYS use print() to show any output (such as column names, head, summary, or results). "
        "Assume the DataFrame is named 'df' and is already loaded. "
        "If you use a column or field that may not exist, always use a try/except block. "
        "In the except block, print a helpful message and then print the following summary: "
        "print('Columns:', list(df.columns))\nprint('Rows:', len(df))\nprint(df.head())\nprint(df.describe(include='all'))\n"
        "If the user asks for column names, use: print(list(df.columns))\n"
        "If the user asks for a summary, use: print(df.describe(include='all'))\n"
        "If the user asks for info, use: print(df.info())\n"
        "If the user asks for the first few rows, use: print(df.head())\n"
        "If the user asks for the number of rows, use: print(len(df))\n"
        "If the user asks for the mean of a column 'age', use: print(df['age'].mean())\n"
        "If the user asks for the sum of a column 'sales', use: print(df['sales'].sum())\n"
        "If the user asks for the unique values in a column 'country', use: print(df['country'].unique())\n"
        "If the user asks for the value counts of a column 'city', use: print(df['city'].value_counts())\n"
        "If the user asks for the largest value in a column 'score', use: print(df['score'].max())\n"
        "If the user asks for the groupby sum of 'new_cases' by 'country', use: print(df.groupby('country')['new_cases'].sum())\n"
        "If the user asks for the top 3 countries by 'new_cases', use: print(df.groupby('country')['new_cases'].sum().nlargest(3))\n"
        "NEVER include import statements, markdown, comments, or explanations. ONLY return the pandas code.\n"
        "If a schema is provided, use it to inform your code. "
        "Always ensure your code is valid Python and all print statements are properly closed. "
        "\n\n"
        "EXAMPLES:\n"
        "Q: What are the column names?\nA: print(list(df.columns))\n"
        "Q: Show the first 5 rows.\nA: print(df.head())\n"
        "Q: What is the mean of the age column?\nA: print(df['age'].mean())\n"
        "Q: How many unique countries?\nA: print(df['country'].nunique())\n"
        "Q: Show a summary of the data.\nA: print(df.describe(include='all'))\n"
    )
    if schema:
        prompt += f"DataFrame schema: {schema}\n"
    prompt += f"User question: {query}\nPandas code:"

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
            code = result["choices"][0]["message"]["content"].strip()
            if code.startswith("```"):
                code = code.strip('`').strip()
                if code.startswith("python"):
                    code = code[len("python"):].strip()
            return code
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to parse LLM response.")

async def generate_pandas_code(request: QueryRequest):
    code = await call_ollama(request.query, request.schema)
    return QueryResponse(pandas_code=code)

@router.post("/parse", response_model=QueryResponse)
async def parse_query(request: QueryRequest):
    """Convert a natural language query to pandas code using Ollama LLM."""
    return await generate_pandas_code(request)
