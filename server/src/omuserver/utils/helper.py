import os
import sys
from pathlib import Path
from typing import List, TypedDict


def safe_path(root: Path, path: Path) -> Path:
    """
    How to prevent directory traversal attack from Python code
    https://stackoverflow.com/a/45190125
    """
    result = root.joinpath(path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f"Path {path} is not relative to {root}")
    return result.relative_to(root.resolve())


def safe_path_join(root: Path, *paths: Path | str) -> Path:
    return root / safe_path(root, root.joinpath(*paths))


class LaunchCommand(TypedDict):
    cwd: str
    args: List[str]


def get_launch_command() -> LaunchCommand:
    return {
        "cwd": os.getcwd(),
        "args": [sys.executable, "-m", "omuserver", *sys.argv[1:]],
    }
