import pathlib
from dataclasses import dataclass
from typing import LiteralString


@dataclass
class Directories:
    data: pathlib.Path
    assets: pathlib.Path
    plugins: pathlib.Path

    @classmethod
    def default(cls):
        cwd = pathlib.Path.cwd()
        return Directories(
            data=cwd / "data",
            assets=cwd / "assets",
            plugins=cwd / "plugins",
        )

    def mkdir(self):
        self.data.mkdir(parents=True, exist_ok=True)
        self.assets.mkdir(parents=True, exist_ok=True)
        self.plugins.mkdir(parents=True, exist_ok=True)

    def to_json(self):
        return {
            "data": str(self.data),
            "assets": str(self.assets),
            "plugins": str(self.plugins),
        }

    def get(self, name: LiteralString):
        path = self.data / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def __post_init__(self):
        self.data = pathlib.Path(self.data)
        self.assets = pathlib.Path(self.assets)
        self.plugins = pathlib.Path(self.plugins)

    def __str__(self):
        return f"Directories(data={self.data}, assets={self.assets}, plugins={self.plugins})"

    def __repr__(self):
        return str(self)
