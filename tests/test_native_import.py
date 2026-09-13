import os
from pathlib import Path
import subprocess
import sys


def test_api_remains_a_package_with_native_pythonpath():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", "import api; assert api.__path__; print(api.__file__)"],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "api")},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert str(root / "api" / "__init__.py") in result.stdout
