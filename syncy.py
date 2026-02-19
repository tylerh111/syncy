"""Sync workspace repositories"""

from __future__ import annotations

import sys

if sys.version_info < (3, 8):
    print(sys.version_info)
    raise Exception("error: python>=3.9 required.")

import argparse
import itertools
import logging
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, ClassVar, Literal, Mapping, Sequence, TypeVar, Union

try:
    import json  # type: ignore
    _HAVE_JSON = True
except ImportError:
    _HAVE_JSON = False

try:
    import tomllib  # type: ignore
    _HAVE_TOMLLIB = True
except ImportError:
    _HAVE_TOMLLIB = False

try:
    import toml  # type: ignore
    _HAVE_TOML = True
except ImportError:
    _HAVE_TOML = False

try:
    import dotenv  # type: ignore
    _HAVE_DOTENV = True
except ImportError:
    _HAVE_DOTENV = False


__version__ = "0.0"

T = TypeVar("T")


##==============================================================
## utils
##==============================================================

def syncy_add_args_if(
    expr: bool,
    *args: str,
) -> Union[tuple[()], tuple[str, ...]]:
    # usage `*syncy_add_args_if(...)`
    return args if expr else ()


##==============================================================
## errors
##==============================================================

class SyncyError(ValueError):
    pass


class SyncyBackendError(SyncyError):
    pass


##==============================================================
## settings
##==============================================================

SYNCY_SETTINGS_FILE: Sequence[str] = [
    ".syncy.toml",
    ".syncy.json",
    ".syncy.env",
]


def _convert_list(s: list | str, sep: str = ";") -> list:
    if isinstance(s, list):
        return s
    return s.split(sep)


@dataclass
class SyncySettings:
    use: str | None = None
    backends: Mapping[str, Any] = field(default_factory=dict)
    source: Path | None = None
    destination: Path | None = None
    exclude: Sequence[str] = field(default_factory=list)
    exclude_from: Sequence[Path] = field(default_factory=list)
    exclude_from_gitignore: bool = False
    include: Sequence[str] = field(default_factory=list)
    include_from: Sequence[Path] = field(default_factory=list)
    dry: bool = False

    # def validate(self) -> bool:

    #     assert src.exists() and src.is_dir()
    #     assert dst.exists() and dst.is_dir()


def _keyval_from_env(env: Mapping[str, str], prefix: str = "syncy") -> Mapping[str, Any]:
    env = {k.lower(): v for k, v in env.items() if k.lower()}
    env = {k: v for k, v in env.items() if k.startswith(f"{prefix}")}

    keyval = [[*k.split("__"), v] for k, v in env.items()]

    res = {}

    for ks in keyval:
        d = res
        for k in ks[:-2]:
            d = d.setdefault(k, {})
        d[ks[-2]] = ks[-1]

    return res


def _keyval_from_file(file: Path) -> Mapping[str, Any]:
    if not file.exists() or not file.is_file():
        return {}

    ext = file.suffixes[-1]
    if ext == ".json" and _HAVE_JSON:
        with file.open() as f:
            contents = json.load(f)
    if ext == ".toml" and _HAVE_TOMLLIB:
        with file.open() as f:
            contents = tomllib.load(f)
    if ext == ".toml" and _HAVE_TOML:
        with file.open() as f:
            contents = toml.load(f)
    if ext == ".env" and _HAVE_DOTENV:
        contents = dotenv.dotenv_values(file)
        contents = _keyval_from_env(contents)

    return contents


# def _keyval_from_args(args: Sequence[str]) -> Mapping[str, Any]:
#     pass


def _try_keyval_from_env(*args, **kwargs) -> Mapping[str, Any]:
    try:
        _keyval_from_env(*args, **kwargs)
    except Exception:
        return {}


def _try_keyval_from_file(*args, **kwargs) -> Mapping[str, Any]:
    try:
        _keyval_from_file(*args, **kwargs)
    except Exception:
        return {}


# def _try_keyval_from_args(*args, **kwargs) -> Mapping[str, Any]:
#     try:
#         _keyval_from_args(*args, **kwargs)
#     except Exception:
#         return {}


def syncy_settings(
    envs: Sequence[Mapping[str, str]] | None = None,
    files: Sequence[Path] | None = None,
    args: Sequence[Sequence[str]] | None = None,
) -> SyncySettings:
    # defaults -> env -> file -> args

    envs = envs or [os.environ]
    files = files or [SYNCY_SETTINGS_FILE]
    args = args or [sys.argv]

    keyvals_envs = [_try_keyval_from_env(env) for env in envs]
    keyvals_files = [_try_keyval_from_file(file) for file in files]
    # keyvals_args = [_try_keyval_from_args(arglist) for arglist in args]

    return SyncySettings()


##==============================================================
## backends
##==============================================================


_syncy_backend_registry: Mapping[str, type] = {}


@dataclass
class SyncyBackend(ABC):
    syncy_backend_enabled: bool = True
    syncy_backend_priority: int = 0

    def __init_subclass__(cls, /, *, backend: str, **kwargs):
        super().__init_subclass__(**kwargs)

        # track registered subclasses for construction
        cls.syncy_backend_name = backend
        _syncy_backend_registry[backend] = cls

    @abstractmethod
    def run(self, settings: SyncySettings):
        ...


def syncy_backend(syncy_backend_name: str, *args, **kwargs) -> SyncyBackend:
    try:
        return _syncy_backend_registry[syncy_backend_name](*args, **kwargs)
    except KeyError as e:
        raise SyncyBackendError(f"unknown syncy backend '{e}'") from None


@dataclass
class SyncyBackendRsync(SyncyBackend, backend="rsync"):
    archive: bool = True  # -a --archive (equivalent: -rlptgoD)
    recursive: bool = False  # -r --recursive
    links: bool = False  # -l --links
    permissions: bool = False  # -p --permissions
    times: bool = False  # -t --times
    group: bool = False  # -g --group
    owner: bool = False  # -o --owner
    devices: bool = False  # --devices
    specials: bool = False  # --specials
    verbose: int = 1  # -v --verbose
    human_readable: bool = True  # -h --human-readable
    partial: bool = True  # --partial
    progress: bool = True  # --progress
    delete: Literal["before"] | Literal["after"] | Literal["during"] | None = None  # --delete-before or --delete-after or --delete-during
    dry: bool = False  # -n --dry
    exclude: Sequence[str] = field(default_factory=list)  # --exclude
    include: Sequence[str] = field(default_factory=list)  # --include

    def command(self, settings: SyncySettings):
        return [
            "rsync",
            *syncy_add_args_if(self.archive,                      "--archive"),
            *syncy_add_args_if(self.recursive,                    "--recursive"),
            *syncy_add_args_if(self.links,                        "--links"),
            *syncy_add_args_if(self.permissions,                  "--permissions"),
            *syncy_add_args_if(self.times,                        "--times"),
            *syncy_add_args_if(self.group,                        "--group"),
            *syncy_add_args_if(self.owner,                        "--owner"),
            *syncy_add_args_if(self.devices,                      "--devices"),
            *syncy_add_args_if(self.specials,                     "--specials"),
            *syncy_add_args_if(self.verbose,                      f"-{'v' * self.verbose}"),
            *syncy_add_args_if(self.human_readable,               "--human-readable"),
            *syncy_add_args_if(self.partial,                      "--partial"),
            *syncy_add_args_if(self.progress,                     "--progress"),
            *syncy_add_args_if(self.delete,                       f"--delete-{self.delete}"),
            *syncy_add_args_if(self.dry or settings.dry,          "--dry"),
            *syncy_add_args_if(self.exclude or settings.exclude,  [f"--exclude={pattern}" for pattern in itertools.chain(self.exclude, settings.exclude)]),
            *syncy_add_args_if(self.include or settings.exclude,  [f"--include={pattern}" for pattern in itertools.chain(self.include, settings.include)]),
            settings.source,
            settings.destination,
        ]

    def run(self, settings: SyncySettings):
        cmd = self.command(settings)


##==============================================================
## run
##==============================================================

def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None):
    argv = argv or []
    env = env or {}

    settings = syncy_settings(argv, env)
    backend = syncy_backend(...)

    print(f"{settings=}")
    print(f"{settings.remaining=}")


if __name__ == "__main__":
    main(sys.argv)
