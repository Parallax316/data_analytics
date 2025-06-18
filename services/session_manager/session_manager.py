import uuid
import tempfile
import shutil
import os
from typing import Dict

# In-memory session store (for demo; use Redis/DB for production)
sessions: Dict[str, dict] = {}

def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {}
    return session_id

def save_file(session_id: str, file):
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, "input.csv")
    file.file.seek(0)
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    sessions[session_id]["file_path"] = file_path

def get_file(session_id: str):
    return sessions[session_id].get("file_path")

def save_profile(session_id: str, profile_output: str):
    sessions[session_id]["profile"] = profile_output

def get_profile(session_id: str):
    return sessions[session_id].get("profile", "")

def append_history(session_id: str, entry: dict):
    if "history" not in sessions[session_id]:
        sessions[session_id]["history"] = []
    sessions[session_id]["history"].append(entry)

def get_history(session_id: str):
    return sessions[session_id].get("history", [])

def save_column_names(session_id: str, column_names: list):
    sessions[session_id]["column_names"] = column_names

def get_column_names(session_id: str):
    return sessions[session_id].get("column_names", [])

def save_docker_state(session_id: str, container_id: str, last_used: float):
    sessions[session_id]["docker_state"] = {
        "container_id": container_id,
        "last_used": last_used
    }

def get_docker_state(session_id: str):
    return sessions[session_id].get("docker_state", None)

def clear_docker_state(session_id: str):
    if "docker_state" in sessions[session_id]:
        del sessions[session_id]["docker_state"]
