from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from services.llm_query_parser.llm_query_parser import QueryRequest, generate_pandas_code
from services.llm_query_parser import llm_query_parser
from services.code_sandbox_mcp.main import run_code_in_sandbox
from services.llm_answer_generator.llm_answer_generator import AnswerRequest, generate_answer
from services.session_manager import session_manager

app = FastAPI(title="Simple Data Agent System")

PROFILE_CODE = (
    "import pandas as pd\n"
    "df = pd.read_csv('input.csv')\n"
    "print(list(df.columns))\n"
)

@app.post("/ask")
async def ask(session_id: str = Form(...), query: str = Form(...)):
    # 1. Get file and profile (columns) from session
    file_path = session_manager.get_file(session_id)
    schema = session_manager.get_profile(session_id)
    # 2. LLM generates code using schema (column names)
    pandas_code_obj = await generate_pandas_code(QueryRequest(query=query, schema=schema))
    pandas_code = pandas_code_obj.pandas_code if hasattr(pandas_code_obj, 'pandas_code') else pandas_code_obj['pandas_code']
    # 3. Run code in Docker using saved file
    result = run_code_in_sandbox(pandas_code, file_path=file_path)
    output = (result["stdout"] or "") + ("\n" + result["stderr"] if result["stderr"] else "")
    # 4. If error or not found, run summary/profile code
    error_triggers = ["not found", "KeyError", "EmptyDataError", "No columns to parse", "not in index"]
    if (not result["success"]) or any(trigger.lower() in output.lower() for trigger in error_triggers) or not result["stdout"].strip():
        summary_result = run_code_in_sandbox(PROFILE_CODE, file_path=file_path)
        output = (summary_result["stdout"] or "") + ("\n" + summary_result["stderr"] if summary_result["stderr"] else "")
    # 5. Summarize the output using the LLM answer agent
    summary = await generate_answer(AnswerRequest(query=query, data_preview=output, columns=schema, code=pandas_code))
    return {
        "answer": summary.answer,
        "pandas_code": pandas_code,
        "sandbox_output": output
    }

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # Create a session and save the uploaded file
    session_id = session_manager.create_session()
    session_manager.save_file(session_id, file)
    file_path = session_manager.get_file(session_id)
    # Run the profile code (only column names)
    result = run_code_in_sandbox(PROFILE_CODE, file_path=file_path)
    output = (result["stdout"] or "") + ("\n" + result["stderr"] if result["stderr"] else "")
    session_manager.save_profile(session_id, output)
    return {
        "session_id": session_id,
        "columns": output.strip()
    }
