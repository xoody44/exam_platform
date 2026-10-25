"""Прямая проверка code_runner: poetry run python -m tools.test_runner"""

from app.database import SessionLocal
from app.models import CodeTest
from app.services.code_runner import run_code_tests


def make_test(expected: str, stdin: str = "") -> CodeTest:
    return CodeTest(
        id=0, sort_order=1, name="check",
        stdin_text=stdin, expected_stdout_text=expected, is_public=False,
    )


def main() -> None:
    db = SessionLocal()
    cases = [
        ("python", 'print("Привет мир")', "", "Привет мир"),
        ("python", "x = int(input())\nprint(x * 2)", "21\n", "42"),
        ("csharp",
         'using System; class P { static void Main() { Console.WriteLine("Привет мир"); } }',
         "", "Привет мир"),
        ("csharp",
         'using System; class P { static void Main() { int x = int.Parse(Console.ReadLine()); Console.WriteLine(x * 2); } }',
         "21\n", "42"),
    ]
    for lang, src, stdin, expected in cases:
        results, log = run_code_tests(
            db=db, language=lang, source=src, tests=[make_test(expected, stdin)]
        )
        status = results[0].status if results else "no-results"
        mark = "OK " if status == "passed" else "FAIL"
        print(f"{mark} {lang:7s} -> {status}")
        if log:
            print("   compile log:", log[:300])


if __name__ == "__main__":
    main()