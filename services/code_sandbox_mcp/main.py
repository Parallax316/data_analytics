from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
import shutil
import tempfile
import os
import subprocess
import uuid
import time
from typing import Optional
from services.session_manager.session_manager import get_docker_state, save_docker_state, clear_docker_state

app = FastAPI(title="Code Sandbox MCP Server")

class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    success: bool

DOCKER_IMAGE = "python:3.11-slim"
REQUIRED_PACKAGES = "pandas"

# Persistent Docker management
import docker

def get_or_create_persistent_container(session_id: str, image: str = DOCKER_IMAGE, timeout: int = 300) -> Optional[str]:
    client = docker.from_env()
    state = get_docker_state(session_id)
    now = time.time()
    if state:
        container_id = state["container_id"]
        last_used = state["last_used"]
        # If container is still within timeout, reuse
        if now - last_used < timeout:
            try:
                container = client.containers.get(container_id)
                if container.status == 'running':
                    save_docker_state(session_id, container_id, now)
                    return container_id
            except Exception:
                pass
        # Otherwise, remove old container
        try:
            container = client.containers.get(container_id)
            container.remove(force=True)
        except Exception:
            pass
        clear_docker_state(session_id)
    # Create new container
    container = client.containers.run(image, "sleep 3600", detach=True, tty=True)
    save_docker_state(session_id, container.id, now)
    return container.id

def stop_persistent_container(session_id: str):
    client = docker.from_env()
    state = get_docker_state(session_id)
    if state:
        try:
            container = client.containers.get(state["container_id"])
            container.remove(force=True)
        except Exception:
            pass
        clear_docker_state(session_id)

# Lightweight profiling for column extraction
PROFILE_CODE = """
import pandas as pd\ndf = pd.read_csv('input.csv')\nprint(list(df.columns))\n"""

def extract_columns_in_sandbox(file: UploadFile = None, file_path: str = None):
    return run_code_in_sandbox(PROFILE_CODE, file, file_path, mode="profile")

def run_code_in_sandbox(code: str, file: UploadFile = None, file_path: str = None, mode: str = "query"):
    import shutil
    import tempfile
    import os
    import subprocess
    import sys
    tempdir = tempfile.mkdtemp()
    try:
        # Save uploaded CSV as input.csv
        csv_path = os.path.join(tempdir, "input.csv")
        if file_path:
            shutil.copy(file_path, csv_path)
        elif file:
            with open(csv_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        # Debug: print file and script contents
        if not os.path.exists(csv_path):
            print(f"[ERROR] input.csv not found at {csv_path}")
        else:
            file_size = os.path.getsize(csv_path)
            print(f"[DEBUG] input.csv size: {file_size} bytes at {csv_path}")
            if file_size == 0:
                print("[ERROR] input.csv is empty!")
                return {"stdout": "", "stderr": "input.csv is empty!", "success": False}
        # Write the code to script.py
        code_path = os.path.join(tempdir, "script.py")
        with open(code_path, 'w', encoding='utf-8') as f:
            if mode == "profile":
                f.write(code)
            else:
                f.write("import pandas as pd\n")
                f.write("df = pd.read_csv('input.csv')\n")
                f.write(code)
        with open(code_path, 'r', encoding='utf-8') as f:
            print(f"[DEBUG] script.py contents:\n{f.read()}")
        # Convert tempdir to Docker-compatible path if on Windows
        mount_dir = tempdir
        if sys.platform.startswith("win"):
            mount_dir = tempdir.replace("\\", "/")
            if ":" in mount_dir:
                drive, rest = mount_dir.split(":", 1)
                mount_dir = f"/{drive.lower()}{rest}"
        # Build the docker run command
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{mount_dir}:/sandbox",
            "-w", "/sandbox",
            DOCKER_IMAGE,
            "sh", "-c",
            f"pip install {REQUIRED_PACKAGES} >/dev/null 2>&1 && python script.py"
        ]
        print(f"[DEBUG] Running Docker command: {' '.join(docker_cmd)}")
        result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=60)
        print(f"[DEBUG] STDOUT: {result.stdout}")
        print(f"[DEBUG] STDERR: {result.stderr}")
        print(f"[DEBUG] Return code: {result.returncode}")
        if result.returncode != 0:
            print(f"[ERROR] Docker run failed. Check input.csv and script.py above.")
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        print("[ERROR] Execution timed out.")
        return {"stdout": "", "stderr": "Execution timed out.", "success": False}
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return {"stdout": "", "stderr": str(e), "success": False}
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)

@app.post("/execute", response_model=ExecutionResult)
async def execute_code(
    code: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Accepts pandas code and a CSV file, runs the code in a Docker sandbox, and returns the output.
    """
    result = run_code_in_sandbox(code, file)
    return ExecutionResult(
        stdout=result["stdout"],
        stderr=result["stderr"],
        success=result["success"]
    )
