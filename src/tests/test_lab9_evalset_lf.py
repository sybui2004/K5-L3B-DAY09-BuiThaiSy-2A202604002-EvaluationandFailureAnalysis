"""The eval-set SHA is part of every report; it must not depend on the OS that built the file."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.student


def test_build_writes_lf_only(tmp_path):
    source = tmp_path / "data/public_claims.jsonl"
    source.parent.mkdir()
    source.write_bytes((json.dumps({"claim_id": "C-001", "matrix_id": "T01", "expected": {"refund_vnd": 1}}) + "\n").encode())
    subprocess.run([sys.executable, "-m", "lab9.evalset", "--build"], cwd=tmp_path, check=True, capture_output=True,
                   env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])})
    assert b"\r\n" not in (tmp_path / "data/eval/eval_set_v1.jsonl").read_bytes()
