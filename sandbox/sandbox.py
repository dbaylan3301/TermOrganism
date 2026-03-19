import shutil
import subprocess
import tempfile
from pathlib import Path

def run_python(file_path: str):
    tmpdir = tempfile.mkdtemp(prefix="organism_")
    dst = Path(tmpdir) / Path(file_path).name
    shutil.copy(file_path, dst)

    p = subprocess.run(
        ["python3", "-m", "py_compile", str(dst)],
        capture_output=True,
        text=True
    )
    if p.returncode != 0:
        return p.returncode, p.stdout, p.stderr

    p2 = subprocess.run(
        ["python3", str(dst)],
        capture_output=True,
        text=True
    )
    return p2.returncode, p2.stdout, p2.stderr
