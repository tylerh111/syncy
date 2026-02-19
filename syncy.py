"""Sync Workspace"""

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
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Literal,
    Mapping,
    Sequence,
    TypeVar,
    Union,
    final,
    overload,
)

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

@final
class Undefined:
    __slots__: tuple[str, ...] = ()
    __instance__: "Undefined"

    def __new__(cls, /) -> "Undefined":
        try:
            return cls.__dict__["__instance__"]
        except KeyError:
            cls.__instance__ = super().__new__(cls)
            return cls.__instance__

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: "Undefined") -> bool:
        return self is other

    def __hash__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "undefined"


undefined = Undefined()


def is_undefined(o: object, /) -> bool:
    return o is undefined


def default_to(o: T, v: T) -> T:
    return v if is_undefined(o) else o


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
## backends
##==============================================================


_syncy_backend_registry: Mapping[str, "SyncyBackend"] = {}


class SyncyBackend(ABC):

    @dataclass
    class Settings:
        syncy_backend_name     : ClassVar[str]
        syncy_backend_enabled  : bool          = True
        syncy_backend_priority : int           = 0

        @classmethod
        def arguments(cls, /, group: argparse.ArgumentParser):
            group.add_argument(f"--{cls.syncy_backend_name}-enabled")
            group.add_argument(f"--{cls.syncy_backend_name}-priority")



    def __init_subclass__(cls, /, *, backend: str, **kwargs):
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, "Settings") or not issubclass(cls.Settings, SyncyBackend.Settings):
            raise TypeError(f"cannot instantiate class {cls.__name__} without inner class `Settings`")

        # track registered subclasses for construction
        cls.Settings.syncy_backend_name = backend
        _syncy_backend_registry[backend] = cls

    # @abstractmethod
    # def run(self, settings: SyncySettings):
    #     pass


def syncy_backend(syncy_backend_name: str) -> type[SyncyBackend]:
    try:
        return _syncy_backend_registry[syncy_backend_name]
    except KeyError as e:
        raise SyncyBackendError(f"unknown syncy backend '{e}'") from None



class SyncyBackendRsync(SyncyBackend, backend="rsync"):

    @dataclass
    class Settings(SyncyBackend.Settings):
        archive        : bool          = True                         # -a --archive (equivalent: -rlptgoD)
        recursive      : bool          = False                        # -r --recursive
        links          : bool          = False                        # -l --links
        permissions    : bool          = False                        # -p --permissions
        times          : bool          = False                        # -t --times
        group          : bool          = False                        # -g --group
        owner          : bool          = False                        # -o --owner
        devices        : bool          = False                        # --devices
        specials       : bool          = False                        # --specials
        verbose        : int           = 1                            # -v --verbose
        human_readable : bool          = True                         # -h --human-readable
        partial        : bool          = True                         # --partial
        progress       : bool          = True                         # --progress
        delete         : Literal["before"] | Literal["after"] | Literal["during"] | None = None  # --delete-before or --delete-after or --delete-during
        dry            : bool          = False                        # -n --dry
        exclude        : Sequence[str] = field(default_factory=list)  # --exclude
        include        : Sequence[str] = field(default_factory=list)  # --include

        @classmethod
        def arguments(cls, /, group: argparse.ArgumentParser):
            super().arguments(group)
            group.add_argument("--rsync-archive")
            group.add_argument("--rsync-recursive")
            group.add_argument("--rsync-links")
            group.add_argument("--rsync-permissions")
            group.add_argument("--rsync-times")
            group.add_argument("--rsync-group")
            group.add_argument("--rsync-owner")
            group.add_argument("--rsync-devices")
            group.add_argument("--rsync-specials")
            group.add_argument("--rsync-verbose")
            group.add_argument("--rsync-human_readable")
            group.add_argument("--rsync-partial")
            group.add_argument("--rsync-progress")
            group.add_argument("--rsync-delete")
            group.add_argument("--rsync-dry")
            group.add_argument("--rsync-exclude")
            group.add_argument("--rsync-include")

    # @classmethod
    # def command(cls, syncy: SyncySettings, rsync: SyncyBackendRsync.Settings):
    #     return [
    #         "rsync",
    #         *syncy_add_args_if(rsync.archive,                   "--archive"               ),
    #         *syncy_add_args_if(rsync.recursive,                 "--recursive"             ),
    #         *syncy_add_args_if(rsync.links,                     "--links"                 ),
    #         *syncy_add_args_if(rsync.permissions,               "--permissions"           ),
    #         *syncy_add_args_if(rsync.times,                     "--times"                 ),
    #         *syncy_add_args_if(rsync.group,                     "--group"                 ),
    #         *syncy_add_args_if(rsync.owner,                     "--owner"                 ),
    #         *syncy_add_args_if(rsync.devices,                   "--devices"               ),
    #         *syncy_add_args_if(rsync.specials,                  "--specials"              ),
    #         *syncy_add_args_if(rsync.verbose,                   f"-{'v' * rsync.verbose}" ),
    #         *syncy_add_args_if(rsync.human_readable,            "--human-readable"        ),
    #         *syncy_add_args_if(rsync.partial,                   "--partial"               ),
    #         *syncy_add_args_if(rsync.progress,                  "--progress"              ),
    #         *syncy_add_args_if(rsync.delete,                    f"--delete-{rsync.delete}"),
    #         *syncy_add_args_if(rsync.dry or syncy.dry,          "--dry"                   ),
    #         *syncy_add_args_if(rsync.exclude or syncy.exclude,  [f"--exclude={pattern}" for pattern in itertools.chain(rsync.exclude, syncy.exclude)]),
    #         *syncy_add_args_if(rsync.include or syncy.exclude,  [f"--include={pattern}" for pattern in itertools.chain(rsync.include, syncy.include)]),
    #         syncy.source,
    #         syncy.destination,
    #     ]  # fmt: skip

    # def run(self, settings: SyncySettings):
    #     cmd = self.command(settings)


##==============================================================
## settings
##==============================================================

SYNCY_SETTINGS_FILE: Sequence[str] = [
    ".syncy.toml",
    # ".syncy.json",
    # ".syncy.env",
]


@dataclass
class SyncySettings:
    use                    : str | None                          = None
    backends               : Mapping[str, SyncyBackend.Settings] = field(default_factory=dict)
    source                 : Path | None                         = None
    destination            : Path | None                         = None
    exclude                : Sequence[str]                       = field(default_factory=list)
    exclude_from           : Sequence[Path]                      = field(default_factory=list)
    exclude_from_gitignore : bool                                = False
    include                : Sequence[str]                       = field(default_factory=list)
    include_from           : Sequence[Path]                      = field(default_factory=list)
    dry                    : bool                                = False

    @classmethod
    def arguments(cls, /, group: argparse.ArgumentParser):
        group.add_argument("-b", "--use")
        group.add_argument("-o", "--destination")
        group.add_argument("--exclude")
        group.add_argument("--exclude-from")
        group.add_argument("--exclude-from-gitignore")
        group.add_argument("--include")
        group.add_argument("--include-from")
        group.add_argument("-r", "--dry")
        group.add_argument("source")



def syncy_default_args() -> Sequence[str]:
    return {**sys.argv}


def syncy_default_envs() -> Mapping[str, str]:
    return {**os.environ}


def syncy_default_file(
    files: Sequence[Path],
    start: Path | None = None,
    _raise: bool = True,
) -> Path | None:
    path = start if start is not None else Path.cwd()
    path = path.absolute()
    while path.parents:
        for file in files:
            if (path / file).is_file():
                return path / file
        else:
            path = path.parent

    if _raise:
        raise FileNotFoundError(f"could not find config file (up to mount point {start})")
    return None


def _argument_parser():
    parser = argparse.ArgumentParser("syncy", exit_on_error=False)
    SyncySettings.arguments(parser.add_argument_group("general"))
    for name, backend in _syncy_backend_registry.items():
        backend.Settings.arguments(parser.add_argument_group(name))

    return parser


def syncy_parse_envs(
    envs: Mapping[str, str],
    prefix: str = "syncy",
) -> Mapping[str, Any]:
    # env vars in the following form:
    # syncy__<field>
    # syncy__backend__<backend>__<field>
    envs = {k.lower(): v for k, v in envs.items() if k.lower()}
    envs = {k: v for k, v in envs.items() if k.startswith(f"{prefix}")}

    keyval = [[*k.split("__"), v] for k, v in envs.items()]

    res = {}

    for ks in keyval:
        d = res
        for k in ks[:-2]:
            d = d.setdefault(k, {})
        d[ks[-2]] = ks[-1]

    return res


def syncy_parse_file(file: Path) -> Mapping[str, Any]:
    if not isinstance(file, Path):
        file = Path(file)

    if not file.exists() or not file.is_file():
        return {}

    ext = file.suffixes[-1]
    if ext == ".json" and _HAVE_JSON:
        with file.open("r", encoding="utf-8") as f:
            contents = json.load(f)
    if ext == ".toml" and _HAVE_TOMLLIB:
        with file.open("rb") as f:
            contents = tomllib.load(f)
    if ext == ".toml" and _HAVE_TOML:
        with file.open("r", encoding="utf-8") as f:
            contents = toml.load(f)
    if ext == ".env" and _HAVE_DOTENV:
        contents = dotenv.dotenv_values(file)
        contents = syncy_parse_envs(contents)

    return contents


def syncy_parse_args(argv: list[str]) -> Mapping[str, Any]:
    try:
        parser = _argument_parser()
        args = parser.parse_args(argv)
        return vars(args)
    except argparse.ArgumentError:
        return {}


def syncy_settings_underlying(
    argv: Sequence[str] | None = None,
    envs: Mapping[str, str] | None = None,
    file: Path | None = None,
) -> SyncySettings:
    # defaults < env < file < args
    settings = {"syncy": {}}

    # parse os env
    if envs is not None:
        settings |= syncy_parse_envs(envs)

    # parse config file
    if file is not None:
        settings |= syncy_parse_file(file)

    # parse cli args
    if argv is not None:
        settings |= syncy_parse_args(argv)

    return settings


def syncy_settings(
    argv: Sequence[str] | None = None,
    envs: Mapping[str, str] | None = None,
    file: Path | None = None,
) -> SyncySettings:
    # defaults < env < file < args
    settings = syncy_settings_underlying(argv, envs, file)
    settings = SyncySettings(**settings["syncy"])
    if settings.use is None:
        raise SyncyError("no backend provided")

    return settings


##==============================================================
## run
##==============================================================

def syncy(
    argv: Sequence[str] | None = None,
    envs: Mapping[str, str] | None = None,
    file: Path | None = None,
):
    if argv is None:
        argv = [*sys.argv]
    if envs is None:
        envs = {**os.environ}
    if file is None:
        file = syncy_default_file(SYNCY_SETTINGS_FILE, _raise=False)

    settings = syncy_settings(argv, envs, file)
    backend = syncy_backend(settings.use)

    print(f"{settings=}")
    print(f"{backend=}")
    # print(f"{settings.remaining=}")


if __name__ == "__main__":
    syncy()
