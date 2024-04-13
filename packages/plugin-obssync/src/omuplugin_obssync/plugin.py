from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, List, TypedDict

import psutil
from omu.identifier import Identifier
from omuserver.server import Server

IDENTIFIER = Identifier("cc.omuchat", "plugin-obssync")


class obs:
    launch_command: List[str] | None = None
    cwd: Path | None = None


def kill_obs():
    for proc in psutil.process_iter():
        if proc.name() == "obs":
            obs.launch_command = proc.cmdline()
            obs.cwd = Path(proc.cwd())
            proc.kill()


def launch_obs():
    if obs.launch_command:
        subprocess.Popen(obs.launch_command, cwd=obs.cwd)


class ScriptToolJson(TypedDict):
    path: str
    settings: Any


ModulesJson = TypedDict("ModulesJson", {"scripts-tool": List[ScriptToolJson]})


def get_launch_command():
    import os
    import sys

    return {
        "cwd": os.getcwd(),
        "args": [sys.executable, "-m", "omuserver", *sys.argv[1:]],
    }


def generate_launcher_code():
    return f"""\
import subprocess
class g:
    process: subprocess.Popen | None = None

def _launch():
    if g.process:
        _kill()
    g.process = subprocess.Popen(**{get_launch_command()})
    print("Launched")

def _kill():
    if g.process:
        g.process.kill()
        g.process = None
        print("Killed")

# obs
def script_load(settings):
    _launch()

def script_unload():
    _kill()
"""


def get_scene_folder():
    import os
    import sys

    if sys.platform == "win32":
        APP_DATA = os.getenv("APPDATA")
        if not APP_DATA:
            raise Exception("APPDATA not found")
        return Path(APP_DATA) / "obs-studio" / "basic" / "scenes"
    else:
        return Path("~/.config/obs-studio/basic/scenes").expanduser()


def install(launcher: Path, scene: Path):
    data: SceneJson = json.loads(scene.read_text(encoding="utf-8"))
    if "modules" not in data:
        data["modules"] = {}
    if "scripts-tool" not in data["modules"]:
        data["modules"]["scripts-tool"] = []
    data["modules"]["scripts-tool"].append({"path": str(launcher), "settings": {}})
    scene.write_text(json.dumps(data), encoding="utf-8")


def install_all_scene():
    launcher = Path(__file__).parent / "_launcher.py"
    launcher.write_text(generate_launcher_code())
    scene_folder = get_scene_folder()
    for scene in scene_folder.glob("*.json"):
        install(launcher, scene)


class SceneJson(TypedDict):
    modules: ModulesJson


async def on_start_server(server: Server) -> None:
    kill_obs()
    install_all_scene()
    launch_obs()
