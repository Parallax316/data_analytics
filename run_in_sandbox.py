import argparse
import os
import subprocess
import tempfile
import shutil

DOCKER_IMAGE = "python:3.11-slim"
REQUIRED_PACKAGES = "pandas"

parser = argparse.ArgumentParser(description="Run pandas code in a sandboxed Docker environment.")
parser.add_argument('--code', type=str, required=True, help='Pandas code to execute (as a string).')
parser.add_argument('--csv', type=str, required=True, help='Path to the CSV file to use as input.')
args = parser.parse_args()

# Create a temporary directory to hold the code and CSV
with tempfile.TemporaryDirectory() as tempdir:
    # Copy the CSV file into the tempdir as input.csv
    csv_dest = os.path.join(tempdir, "input.csv")
    shutil.copy(args.csv, csv_dest)

    # Write the code to a script file
    code_path = os.path.join(tempdir, "script.py")
    with open(code_path, 'w', encoding='utf-8') as f:
        f.write(f"import pandas as pd\n")
        f.write(f"df = pd.read_csv('input.csv')\n")
        # Write the user code, skipping redundant import and read_csv
        user_code = args.code.strip()
        user_code = user_code.replace('import pandas as pd', '').replace('df = pd.read_csv(', '# df = pd.read_csv(')
        f.write(user_code + "\n")

    # Build the docker run command
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{tempdir}:/sandbox",
        "-w", "/sandbox",
        DOCKER_IMAGE,
        "sh", "-c",
        f"pip install {REQUIRED_PACKAGES} >/dev/null 2>&1 && python script.py"
    ]

    print(f"[INFO] Running code in Docker sandbox...\n")
    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=60)
        print("[STDOUT]\n" + result.stdout)
        if result.stderr:
            print("[STDERR]\n" + result.stderr)
    except subprocess.TimeoutExpired:
        print("[ERROR] Execution timed out.")
    except Exception as e:
        print(f"[ERROR] {e}")
