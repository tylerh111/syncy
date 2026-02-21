# MIT License

# Copyright (c) 2025-2026 Tyler Hughes

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Sync Workspaces!"""

from __future__ import annotations

# __name__ = "syncy"
# __doc__ = "Sync Workspaces!"
__version__ = "0.0"
__date__ = "2026-02-20"
__author__ = "Tyler Hughes"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2025-2026 Tyler Hughes"
__all__ = ["syncy"]


import sys

if sys.version_info < (3, 10):
    raise SyntaxError("python>=3.10 required")

import argparse
import itertools
import os
import subprocess
import sys
import warnings
from abc import ABC, abstractmethod
from dataclasses import Field, dataclass, field, fields
from pathlib import Path
from types import NoneType, UnionType
from typing import (
    Any,
    ClassVar,
    Literal,
    TypeAlias,
    TypeVar,
    Union,
    final,
    get_args,
    get_origin,
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


##==============================================================================
## constants
##==============================================================================


T = TypeVar("T")
U = TypeVar("U")


_RsyncDeleteType: TypeAlias = Literal["before", "after", "during", "default"]


SYNCY_SETTINGS_FILE: list[str] = [
    ".syncy.toml",
    # ".syncy.json",
    # ".syncy.env",
]


def syncy_default_args() -> list[str]:
    return [*sys.argv]


def syncy_default_envs() -> dict[str, str]:
    return {**os.environ}


def syncy_default_file(
    start: Path | None = None,
    _raise: bool = True,
) -> Path | None:
    files = SYNCY_SETTINGS_FILE
    path = start if start is not None else Path.cwd()
    path = path.absolute()
    while path.parents:
        for file in files:
            if (path / file).is_file():
                return path / file
        else:
            path = path.parent

    if _raise:
        raise FileNotFoundError(
            f"could not find config file (up to mount point {start})"
        )

    warnings.warn(f"could not find config file (up to mount point {start})")
    return None


##==============================================================================
## errors
##==============================================================================


class SyncyError(ValueError):
    pass


class SyncyBackendError(SyncyError):
    pass


class SyncyValidationError(SyncyError):
    pass


##==============================================================================
## utils
##==============================================================================


@final
class Undefined:
    __slots__: tuple[str, ...] = ()
    __instance__: Undefined

    def __new__(cls, /) -> Undefined:
        try:
            return cls.__dict__["__instance__"]
        except KeyError:
            cls.__instance__ = super().__new__(cls)
            return cls.__instance__

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: Undefined) -> bool:
        return self is other

    def __hash__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "undefined"


undefined = Undefined()


def isundefined(o: object, /) -> bool:
    return o is undefined


def default_to(o: Undefined | T, v: T) -> T:
    return v if isundefined(o) else o


def add_args_if(
    expr: bool,
    *args: str,
) -> tuple[()] | tuple[str, ...]:
    # usage `*add_args_if(...)`
    return args if expr else ()


class _TypeHandler:
    @staticmethod
    def type_check(o: object, t: type) -> bool:
        return (
            _TypeHandler.type_check_none(o, t)
            or _TypeHandler.type_check_undefined(o, t)
            or _TypeHandler.type_check_union(o, t)
            or _TypeHandler.type_check_literal(o, t)
            or _TypeHandler.type_check_list(o, t)
            or _TypeHandler.type_check_dict(o, t)
            or _TypeHandler.type_check_regular(o, t)
        )

    @staticmethod
    def type_check_regular(o: object, t: type[type]) -> bool:
        try:
            return isinstance(o, t)
        except TypeError:
            return False

    @staticmethod
    def type_check_none(o: object, _: NoneType) -> bool:
        return o is None

    @staticmethod
    def type_check_undefined(o: object, _: Undefined) -> bool:
        return isundefined(o)

    @staticmethod
    def type_check_alias(o: object, t: type[UnionType]) -> bool:
        orig = get_origin(t)
        args = get_args(t)
        return any([_TypeHandler.type_check(o, u) for u in args])

    @staticmethod
    def type_check_union(o: object, t: type[UnionType]) -> bool:
        args = get_args(t)
        return any([_TypeHandler.type_check(o, u) for u in args])

    @staticmethod
    def type_check_literal(o: object, t: type[Literal[0]]) -> bool:
        args = get_args(t)
        return o in args  # implicit equality

    @staticmethod
    def type_check_list(o: object, t: type[list[T]]) -> bool:
        if not isinstance(o, list):
            return False

        args = get_args(t)
        subtypesmatch = True
        if args:
            subtypesmatch = all([_TypeHandler.type_check(p, args[0]) for p in o])

        return subtypesmatch

    @staticmethod
    def type_check_dict(o: object, t: type[dict[T, U]]) -> bool:
        if not isinstance(o, dict):
            return False

        args = get_args(t)
        subtypesmatch = True
        if args:
            subtypesmatch &= all(
                [_TypeHandler.type_check(p, args[0]) for p in o.keys()]
            )
            subtypesmatch &= all(
                [_TypeHandler.type_check(p, args[0]) for p in o.values()]
            )

        return subtypesmatch

    @staticmethod
    def type_cast(o: object, t: type) -> bool:
        if not isundefined(p := _TypeHandler.type_cast_union(o, t)):
            return p
        if not isundefined(p := _TypeHandler.type_cast_list(o, t)):
            return p
        if not isundefined(p := _TypeHandler.type_cast_dict(o, t)):
            return p
        if not isundefined(p := _TypeHandler.type_cast_regular(o, t)):
            return p
        return undefined

    @staticmethod
    def type_cast_regular(o: object, t: type[T]) -> T | Undefined:
        if _TypeHandler.type_check_regular(o, t):
            return o
        try:
            return t(o)
        except TypeError:
            return undefined

    @staticmethod
    def type_cast_union(o: object, t: type[UnionType]) -> T | Undefined:
        if _TypeHandler.type_check_union(o, t):
            return o

        args = get_args(t)
        for u in args:
            try:
                return _TypeHandler.type_cast(o, u)
            except TypeError:
                pass

        return undefined

    @staticmethod
    def type_cast_list(o: object, t: type[list[T]]) -> list[T] | Undefined:
        if _TypeHandler.type_check_list(o, t):
            return o

        args = get_args(t)
        if isinstance(o, list) and args:
            return [_TypeHandler.type_cast(v, args[0]) for v in o]

        return undefined

    @staticmethod
    def type_cast_dict(o: object, t: type[dict[T, U]]) -> dict[T, U] | Undefined:
        if _TypeHandler.type_check_dict(o, t):
            return o

        args = get_args(t)
        if isinstance(o, dict) and args:
            return {
                _TypeHandler.type_cast(k, args[1]): _TypeHandler.type_cast(v, args[0])
                for k, v in o.items()
            }

        return undefined

    @staticmethod
    def type_parse(typestr: str) -> type:

        KNOWN_TYPES = {
            "dict": dict,
            "list": list,
            "set": set,
            "bool": bool,
            "int": int,
            "float": float,
            "str": str,
            "None": None,
            "Undefined": Undefined,
            "Literal": Literal,
            "TypeAlias": Literal,
            "Union": Union,
            "Path": Path,
        }

        # Evil eval used to parse the type string into a type. Libraries could
        # be used to properly parse, check, and coarse the type, but with only
        # using built-in python functions, this is the simplest way to do it.
        # This required due to all annotations being saved as string caused by
        # `from __future__ import annotations`. Removing that would remove the
        # need for this function. However, that may cause other issues elsewhere.
        return eval(typestr, globals(), KNOWN_TYPES)


def type_check(
    o: object,
    field: str,
    expected: str | type,
) -> bool:
    t = type(o)
    if isinstance(expected, str):
        _expected = _TypeHandler.type_parse(expected)
    else:
        _expected = expected

    if isundefined(_expected):
        raise TypeError(f"unknown type {expected!r}")

    if isundefined(o):
        raise SyncyValidationError(
            f"validation of field '{field}' failed: "
            f"value undefined: expected a '{expected}' (got '{t}')"
        )

    if not _TypeHandler.type_check(o, _expected):
        raise SyncyValidationError(
            f"validation of field '{field}' failed: "
            f"incorrect type: expected a '{expected}' (got '{t}')"
        )
    return True


def type_cast(
    o: object,
    field: str,
    expected: str | type,
) -> T:
    t = type(o)
    if isinstance(expected, str):
        _expected = _TypeHandler.type_parse(expected)
    else:
        _expected = expected

    if isundefined(_expected):
        raise TypeError(f"unknown type {expected!r}")

    if isundefined(o):
        raise SyncyValidationError(
            f"validation of field '{field}' failed: "
            f"value undefined: expected a '{expected}' (got '{t}')"
        )

    try:
        type_check(o, field, _expected)
        return o
    except SyncyValidationError:
        pass

    p = _TypeHandler.type_cast(o, _expected)
    if isundefined(p):
        raise SyncyValidationError(
            f"validation of field '{field}' failed: "
            f"invalid convertion: tried converting to '{expected}' (from '{t}')"
        )

    return p


def validate(inst: object, field: Field):
    value = getattr(inst, field.name)
    value = type_cast(value, field.name, field.type)
    setattr(inst, field.name, value)


##==============================================================================
## interfaces
##==============================================================================


_syncy_backend_registry: dict[str, Backend] = {}


class Backend(ABC):
    syncy_backend_name: ClassVar[str]

    @dataclass
    class Settings:
        # fmt: off
        syncy_backend_name     : ClassVar[str]
        syncy_backend_enabled  : bool          = True
        syncy_backend_priority : int           = 0
        # fmt: on

        @classmethod
        def arguments(cls, /, group: argparse.ArgumentParser):
            group.add_argument(f"--{cls.syncy_backend_name}-enabled")
            group.add_argument(f"--{cls.syncy_backend_name}-priority")
            for field in fields(cls):
                if field.name not in (
                    "syncy_backend_name",
                    "syncy_backend_enabled",
                    "syncy_backend_priority",
                ):
                    name = field.name.replace("_", "-")
                    group.add_argument(f"--{cls.syncy_backend_name}-{name}")

        def validate(self):
            for field in fields(self):
                if field.name not in ("syncy_backend_name",) and field.type not in (
                    TypeAlias,
                ):
                    validate(self, field)

    def __init__(self, settings: Settings | None = None):
        self.settings = settings

    def __init_subclass__(cls, /, *, backend: str, **kwargs):
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, "Settings"):
            raise TypeError(
                f"cannot subclass backend {cls.__name__} without inner class `Settings`"
            )
        if not issubclass(cls.Settings, Backend.Settings):
            raise TypeError(
                f"cannot subclass backend {cls.__name__} without "
                f"inner class `Settings` inheriting `syncy.Backend.Settings"
            )

        # track registered subclasses for construction
        cls.syncy_backend_name = backend
        cls.Settings.syncy_backend_name = backend
        _syncy_backend_registry[backend] = cls

    @classmethod
    def lookup(cls, syncy_backend_name: str, /) -> type[Backend]:
        try:
            return _syncy_backend_registry[syncy_backend_name]
        except KeyError as e:
            raise SyncyBackendError(f"unknown syncy backend '{e}'") from None

    @abstractmethod
    def run(self, settings: Syncy.Settings):
        pass


##==============================================================================
## backends
##==============================================================================


# special type of backend that defers execution based on `use`
class Syncy(Backend, backend="general"):
    @dataclass
    class Settings(Backend.Settings):
        # fmt: off
        use                    : str                         = undefined
        backends               : dict[str, Backend.Settings] = field(default_factory=dict)
        source                 : Path                        = undefined
        destination            : Path                        = undefined
        exclude                : list[str]                   = field(default_factory=list)
        exclude_from           : list[Path]                  = field(default_factory=list)
        exclude_from_gitignore : bool                        = False
        include                : list[str]                   = field(default_factory=list)
        include_from           : list[Path]                  = field(default_factory=list)
        dry                    : bool                        = False
        # fmt: on

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

        def validate(self):
            self.backends = {
                name: Backend.lookup(name).Settings(**settings)
                for name, settings in self.backends.items()
            }

            for field in fields(self):
                if field.name not in ("backends",):
                    validate(self, field)

            for backend in self.backends.values():
                backend.validate()

    def run(self, settings: Syncy.Settings):
        _Backend = Backend.lookup(settings.use)
        relative = settings.backends.get(settings.use, _Backend.Settings())
        backend = _Backend(relative)
        backend.run(settings)


class SyncyBackendRsync(Backend, backend="rsync"):
    @dataclass
    class Settings(Backend.Settings):
        # fmt: off
        archive        : bool             = True       # -a --archive (equivalent: -rlptgoD)
        recursive      : bool             = False      # -r --recursive
        links          : bool             = False      # -l --links
        permissions    : bool             = False      # -p --permissions
        times          : bool             = False      # -t --times
        group          : bool             = False      # -g --group
        owner          : bool             = False      # -o --owner
        devices        : bool             = False      # --devices
        specials       : bool             = False      # --specials
        verbose        : int              = 1          # -v --verbose
        human_readable : bool             = True       # -h --human-readable
        partial        : bool             = True       # --partial
        progress       : bool             = True       # --progress
        delete         : _RsyncDeleteType = "default"  # --delete-{before, after, during} or use default
        dry            : bool             = False      # -n --dry
        exclude        : list[str]        = field(default_factory=list)  # --exclude
        include        : list[str]        = field(default_factory=list)  # --include
        # fmt: on

    def command(
        cls,
        syncy: Syncy.Settings,
        rsync: SyncyBackendRsync.Settings,
    ) -> list[str]:
        return [
            "rsync",
            *add_args_if(rsync.archive,             "--archive"               ),
            *add_args_if(rsync.recursive,           "--recursive"             ),
            *add_args_if(rsync.links,               "--links"                 ),
            *add_args_if(rsync.permissions,         "--permissions"           ),
            *add_args_if(rsync.times,               "--times"                 ),
            *add_args_if(rsync.group,               "--group"                 ),
            *add_args_if(rsync.owner,               "--owner"                 ),
            *add_args_if(rsync.devices,             "--devices"               ),
            *add_args_if(rsync.specials,            "--specials"              ),
            *add_args_if(rsync.verbose,             f"-{'v' * rsync.verbose}" ),
            *add_args_if(rsync.human_readable,      "--human-readable"        ),
            *add_args_if(rsync.partial,             "--partial"               ),
            *add_args_if(rsync.progress,            "--progress"              ),
            *add_args_if(rsync.delete != "default", f"--delete-{rsync.delete}"),
            *add_args_if(rsync.dry or syncy.dry,    "--dry-run"               ),
            *add_args_if(rsync.exclude or syncy.exclude, [
                f"--exclude={pattern}" for pattern in itertools.chain(rsync.exclude, syncy.exclude)
            ]),
            *add_args_if(rsync.include or syncy.exclude, [
                f"--include={pattern}" for pattern in itertools.chain(rsync.include, syncy.include)
            ]),
            syncy.source.as_posix(),
            syncy.destination.as_posix(),
        ]  # fmt: skip

    def run(self, syncy: Syncy.Settings):
        rsync = self.settings
        cmd = self.command(syncy, rsync)
        cont = input(f"executing: {' '.join(map(str, cmd))} \ncontinue? [y/N] ")
        if not cont.lower().startswith("y"):
            return
        subprocess.run(cmd, check=True)


##==============================================================================
## run
##==============================================================================


def _argument_parser():
    parser = argparse.ArgumentParser(
        "syncy",
        add_help=True,
        exit_on_error=False,
        usage="%(prog)s [-h] [-b backend] [-r] source [destination ...]",
    )
    for name, backend in _syncy_backend_registry.items():
        backend.Settings.arguments(parser.add_argument_group(name))

    return parser


def syncy_parse_args(argv: list[str]) -> dict[str, Any]:
    try:
        parser = _argument_parser()
        args = parser.parse_args(argv)
        return vars(args)
    except argparse.ArgumentError:
        return {}


def syncy_parse_envs(
    envs: dict[str, str],
    prefix: str = "syncy",
) -> dict[str, Any]:
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


def syncy_parse_file(file: Path) -> dict[str, Any]:
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


def syncy_settings_underlying(
    argv: list[str] | None = None,
    envs: dict[str, str] | None = None,
    file: Path | None = None,
) -> Syncy.Settings:
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
    argv: list[str] | None = None,
    envs: dict[str, str] | None = None,
    file: Path | None = None,
) -> Syncy.Settings:
    # defaults < env < file < args
    settings = syncy_settings_underlying(argv, envs, file)
    settings = Syncy.Settings(**settings["syncy"])
    if settings.use is None:
        raise SyncyError("no backend provided")

    print(settings.backends)
    settings.validate()
    print(settings.backends)

    return settings


def syncy(
    argv: list[str] | None = None,
    envs: dict[str, str] | None = None,
    file: Path | None = None,
):
    if argv is None:
        argv = syncy_default_args()
    if envs is None:
        envs = syncy_default_envs()
    if file is None:
        file = syncy_default_file(_raise=False)

    settings = syncy_settings(argv, envs, file)

    entrypoint = Syncy()
    entrypoint.run(settings)


def entrypoint():
    try:
        syncy()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    entrypoint()
