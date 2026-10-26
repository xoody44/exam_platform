import os
import shutil
import subprocess
import sys
import tempfile
import ctypes
from dataclasses import asdict, dataclass
from pathlib import Path

from ..config import get_settings
from ..models import (
    LANG_CSHARP,
    LANG_PYTHON,
    TEST_COMPILE_ERROR,
    TEST_PASSED,
    TEST_RUNTIME_ERROR,
    TEST_TIMEOUT,
    TEST_WRONG_ANSWER,
    CodeTest,
)

CREATE_NO_WINDOW = 0x08000000
COMPILE_TIMEOUT = 30
MAX_OUTPUT_BYTES = 1_000_000


def _oem_cp() -> str:
    try:
        return f"cp{ctypes.windll.kernel32.GetOemCP()}"
    except Exception:
        return "cp866"


def _ansi_cp() -> str:
    try:
        return f"cp{ctypes.windll.kernel32.GetACP()}"
    except Exception:
        return "cp1251"


@dataclass
class TestResult:
    test_id: int
    sort_order: int
    name: str
    status: str
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _minimal_env() -> dict:
    system_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
    temp = os.environ.get("TEMP", tempfile.gettempdir())
    return {
        "SYSTEMROOT": system_root,
        "TEMP": temp,
        "TMP": temp,
        "PATH": system_root + r"\System32;" + system_root,
        "PYTHONIOENCODING": "utf-8",
    }


def _normalize_output(text: str) -> str:
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _decode_output(data: bytes, language: str) -> str:
    if language == LANG_PYTHON:
        order = ("utf-8", _ansi_cp(), _oem_cp())
    else:
        order = (_oem_cp(), "utf-8", _ansi_cp())
    for enc in order:
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _encode_input(text: str, language: str) -> bytes:
    if language == LANG_PYTHON:
        return text.encode("utf-8")
    for enc in (_oem_cp(), _ansi_cp()):
        try:
            return text.encode(enc)
        except (UnicodeEncodeError, LookupError):
            continue
    return text.encode("utf-8", errors="replace")


def resolve_python(db) -> str | None:
    from .settings import get_setting

    path = (get_setting(db, "python_executable") or "").strip()
    if path and Path(path).exists():
        return path
    if not getattr(sys, "frozen", False):
        return sys.executable
    return shutil.which("python") or shutil.which("python3")


def resolve_csc(db) -> str | None:
    from .settings import get_setting

    path = (get_setting(db, "csc_path") or "").strip()
    if path and Path(path).exists():
        return path
    found = shutil.which("csc") or shutil.which("csc.exe")
    if found:
        return found
    candidates = [
        r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def _run_one(
    cmd: list[str], input_bytes: bytes, cwd: Path, timeout: float
) -> tuple[str, bytes | None]:
    try:
        proc = subprocess.run(
            cmd,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(cwd),
            env=_minimal_env(),
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return TEST_TIMEOUT, None
    except OSError:
        return TEST_RUNTIME_ERROR, None

    if proc.returncode != 0:
        return TEST_RUNTIME_ERROR, None

    return TEST_PASSED, (proc.stdout or b"")[:MAX_OUTPUT_BYTES]


def run_code_tests(
    *,
    db,
    language: str,
    source: str,
    tests: list[CodeTest],
) -> tuple[list[TestResult], str | None]:
    from .settings import get_setting

    time_limit = max(float(int(get_setting(db, "code_time_limit_seconds"))), 1.0)

    def fail_all(status: str, log: str | None = None):
        return (
            [TestResult(t.id, t.sort_order, t.name, status, False) for t in tests],
            log,
        )

    if not tests:
        return [], None
    workdir = Path(tempfile.mkdtemp(prefix="examcode_"))
    try:
        if language == LANG_PYTHON:
            python = resolve_python(db)
            if python is None:
                return fail_all(
                    TEST_COMPILE_ERROR, "На сервере не настроен python_executable"
                )
            (workdir / "prog.py").write_text(source, encoding="utf-8")
            cmd = [python, "-I", "-B", "prog.py"]

        elif language == LANG_CSHARP:
            csc = resolve_csc(db)
            if csc is None:
                return fail_all(
                    TEST_COMPILE_ERROR, "На сервере не найден компилятор C# (csc.exe)"
                )
            (workdir / "prog.cs").write_text(source, encoding="utf-8")
            try:
                comp = subprocess.run(
                    [csc, "/nologo", "/optimize+", "/out:prog.exe", "prog.cs"],
                    cwd=str(workdir),
                    env=_minimal_env(),
                    capture_output=True,
                    timeout=COMPILE_TIMEOUT,
                    creationflags=CREATE_NO_WINDOW,
                )
            except (subprocess.TimeoutExpired, OSError) as exc:
                return fail_all(TEST_COMPILE_ERROR, f"Сбой компиляции: {exc}")
            if comp.returncode != 0:
                log = comp.stderr.decode("utf-8", errors="replace")[:4000]
                return fail_all(TEST_COMPILE_ERROR, log)
            cmd = [str(workdir / "prog.exe")]
        else:
            return fail_all(TEST_COMPILE_ERROR, f"Неизвестный язык: {language}")

        results: list[TestResult] = []
        for t in tests:
            status, raw = _run_one(
                cmd, _encode_input(t.stdin_text, language), workdir, time_limit
            )
            if status == TEST_PASSED:
                stdout = _decode_output(raw or b"", language)
                ok = _normalize_output(stdout) == _normalize_output(
                    t.expected_stdout_text
                )
                status = TEST_PASSED if ok else TEST_WRONG_ANSWER
            results.append(
                TestResult(t.id, t.sort_order, t.name, status, status == TEST_PASSED)
            )
        return results, None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
