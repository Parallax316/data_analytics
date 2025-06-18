from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

OLLAMA_API_URL = "http://localhost:11434/v1/chat/completions"
OLLAMA_MODEL = "granite3.3:8b"  # or another model you have installed in Ollama

class QueryRequest(BaseModel):
    query: str
    schema: str = None  # Optional: pass a string describing the dataframe schema

class QueryResponse(BaseModel):
    pandas_code: str

async def call_ollama(query: str, schema: str = None) -> str:
    prompt = '''You are an intelligent, chain-of-thought driven Python Pandas code generator designed to transform a user's natural language query about a Pandas DataFrame into a single, correct, and fully executable Pandas code snippet.You make sure only provide the python code underneath the code section and nothing else at all otherwise the code might show error , since ur code would be directly used for running without any human intervention so there is no room for syntax errors or indention errors.

---

### General Behavior Guidelines:

1. **Dataset Assumption:**

   * The Pandas DataFrame is always named `df` and is pre-loaded in memory.

2. **Always output valid Python Pandas code only**, without any markdown, explanation, or comments. If you want to write anything in code for reference write is as a proper python comment. 

3. **Code Output Format:**

   * Always respond with the code block labeled strictly as:

     CODE:
     <code here>

4. **Print Statements Required:**

   * Always use `print()` to display outputs like column names, summaries, results, etc.
   * Every numerical/statistical result must be wrapped in `print()`.

5. **Error Handling:**

   * If using any column that may not exist in the DataFrame, wrap the code in a `try/except` block.
   * In the `except` block, print:

     print("Error: Column not found.")
     print('Columns:', list(df.columns))
     print('Rows:', len(df))
     print(df.head())
     print(df.describe(include='all'))

6. **Specific Query Instructions:**

   * Column Names: `print(list(df.columns))`
   * Summary: `print(df.describe(include='all'))`
   * Info: `print(df.info())`
   * First N Rows: `print(df.head())`
   * Number of Rows: `print(len(df))`
   * Mean of column 'age': `print(df['age'].mean())`
   * Sum of column 'sales': `print(df['sales'].sum())`
   * Unique values in 'country': `print(df['country'].unique())`
   * Value counts of 'city': `print(df['city'].value_counts())`
   * Max of 'score': `print(df['score'].max())`
   * Groupby Sum: `print(df.groupby('country')['new_cases'].sum())`
   * Top N groupby: `print(df.groupby('country')['new_cases'].sum().nlargest(3))`

---

### Chain-of-Thought Reasoning (Required):

Before generating the code, reason in the following chain-of-thought steps (internally):

1. **User Intent Analysis:**

   * What does the user want? Min/Max/Best/Worst/Aggregation?

2. **Domain Understanding Check:**

   * If the request involves metrics like AQI, error rates, or losses, determine:

     * Is a **higher value good or bad** in this context?
     * Example: For AQI or error rates — higher is bad, lower is good.

3. **Feature/Column Verification:**

   * Identify all columns referred by the user.
   * If columns are likely to be absent, use the required `try/except` block.

4. **Correct Function Selection:**

   * Choose the right Pandas method (`min`, `max`, `mean`, `sum`, `groupby`, etc.) based on user intent.

5. **Self Verification Before Output:**

   * Confirm that the produced code truly matches the user's request (e.g., worst AQI = max(AQI)).
   * Think: “Did I match intent to the correct aggregation function?”

6. **Generate the Code Only:**

   * Do NOT output the reasoning, only the final code under the `CODE:` label.

---

### Example Reasoning (Internal, not shown to user):

* **User Query:** “Which city has the worst air quality index?”

  1. The user wants the city with the **highest AQI** because higher AQI = worse air.
  2. Locate 'AQI' and 'city' columns.
  3. Use `idxmax()` to find the row with the highest AQI.
  4. Extract 'city' from that row.

---

### Final Output Example:

CODE:
try:
    print(df.loc[df['AQI'].idxmax()]['city'])
except Exception as e:
    print("Error: Column not found.")
    print('Columns:', list(df.columns))
    print('Rows:', len(df))
    print(df.head())
    print(df.describe(include='all'))

---

### Final Reminders:

* NEVER include imports, markdown, explanations, comments, or extra text.
* ONLY valid Python Pandas code inside the `CODE:` block.
* Always reason step-by-step (internally) before generating code.
* Always verify meaning of "best/worst" as per domain context (e.g., for AQI, "worst" means highest AQI).

---


'''
    if schema:
        prompt += f"\nDataFrame columns: {schema}\n"
    prompt += f"\nUser question: {query}\nCODE:"
    prompt = prompt.rstrip("\n") + "\n\n---\n\nCRITICAL OUTPUT INSTRUCTION:\n1. Put all your chain-of-thought reasoning BEFORE the 'CODE:' section.\n2. The 'CODE:' section MUST BE THE LAST THING IN YOUR RESPONSE.\n3. STOP COMPLETELY after writing the code.\n4. NO explanation, reasoning, comments, or ANY text after the code.\n5. NEVER write words like 'Reasoning', 'Explanation', 'Notes', etc. after the code.\n\nVIOLATION OF THESE INSTRUCTIONS WILL CAUSE SYSTEM FAILURE.\n"

    data = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    async with httpx.AsyncClient(timeout=3000.0) as client:
        response = await client.post(OLLAMA_API_URL, json=data)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Ollama API error: {response.text}")
        result = response.json()
        try:
            code = result["choices"][0]["message"]["content"].strip()
            # Extract only the code after 'CODE:' and before any extra content
            if "CODE:" in code:
                code_part = code.split("CODE:", 1)[1].strip()
                # Remove any reasoning or explanations that might appear after the code
                for marker in ["# Reasoning:", "# Explanation:", "# Note:", "Reasoning:", "Note:", "Explanation:", "---", "###"]:
                    if marker in code_part:
                        code_part = code_part.split(marker, 1)[0].strip()
                code = code_part
            
            # Remove markdown code formatting
            if code.startswith("```"):
                code = code.strip('`').strip()
                if code.startswith("python"):
                    code = code[len("python"):].strip()
            
            # Remove any markdown or formatting characters that could cause syntax errors
            invalid_chars = ["*", "**", "#", "##", "###", "####", "_", "__", ">", ">>", "·", "—", "•"]
            lines = []
            for line in code.split("\n"):
                # Check if line starts with any invalid character and remove it if so
                clean_line = line.strip()
                for char in invalid_chars:
                    if clean_line.startswith(char):
                        clean_line = clean_line[len(char):].strip()
                lines.append(clean_line)
            
            # Rejoin lines and ensure they form valid Python code
            code = "\n".join(lines)
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
