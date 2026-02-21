import re
from pathlib import Path


def increment_version():
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("pyproject.toml not found")
        return

    content = pyproject_path.read_text(encoding="utf-8")

    # Simple regex to find the version in [project] section
    # Matches version = "x.y.z"
    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content, re.MULTILINE)

    if not match:
        print("Version not found in pyproject.toml")
        return

    major, minor, patch = map(int, match.groups())
    new_version = f"{major}.{minor}.{patch + 1}"

    new_content = re.sub(
        r'^version\s*=\s*"\d+\.\d+\.\d+"',
        f'version = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE
    )

    pyproject_path.write_text(new_content, encoding="utf-8")
    print(f"Version incremented to {new_version}")

if __name__ == "__main__":
    increment_version()
