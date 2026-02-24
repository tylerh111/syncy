# Syncy

[![_](https://img.shields.io/pypi/v/syncy)](https://pypi.python.org/pypi/syncy)
[![_](https://img.shields.io/pypi/pyversions/syncy)](https://github.com/tylerh111/syncy)
[![_](https://img.shields.io/pypi/l/syncy)](https://github.com/tylerh111/syncy/blob/main/LICENSE.md)

---

[Syncy](https://github.com/tylerh111/syncy) is a tool for syncing a directory / repository / workspace / etc.
The original use case was to sync a virtual machine's local copy of a workspace with the host's copy via a shared folder.
It can also be used to make backups of directories.
Syncy uses `rsync` for syncing directories, but it is flexible to extend it to other backends.

```bash
more .syncy.toml
#> [syncy]
#> source = "path/to/source"
syncy
#> syncing "." with "path/to/source"
#> ...
```

### Installation

Syncy is available as [`syncy`](https://pypi.python.org/pypi/syncy) on PyPI.

```bash
pip install syncy
```

### Usage

Syncy is specified via a config file named `.syncy.toml`.
The file will be searched for recursively upwards to the root of the filesystem.
By default, the directory where the config file is stored is the destination of the sync.
Note, the `.syncy` file can be either TOML or JSON, and it recommended to use.

Simply call `syncy` from the command line when anywhere within your repository.
Syncy has a few command line options that match the config files.
The priority of configurations follows this order (low to high): defaults, environment, file, arguments.

```bash
syncy
```

### Reference

The following is all the syncy command line options.

> WIP

The following is all the `syncy` configurations.
Environment variables are under `SYNCY_`.
Backend specific variables are under `SYNCY_BACKENDS_<backend>_`.
Note, all environment variables are capitalized.

| Under   | Configuration | Env      | Cmd      | Description                       | Default |
|---------|---------------|:--------:|:--------:|-----------------------------------|---------|
| `syncy` | `backend`     | &#x2705; | &#x2705; | Backend to use                    | `rsync` |
| `syncy` | `source`      | &#x2705; | &#x2705; | Source to sync                    |         |
| `syncy` | `destination` | &#x2705; | &#x2705; | Destination to sync               | `.`     |
| `syncy` | `exclude`     | &#x2705; | &#x274c; | Global list of exclusion patterns | `[]`*   |
| `syncy` | `include`     | &#x2705; | &#x274c; | Global list of inclusion patterns | `[]`*   |

> \* the syncy settings files are excluded by default (even if not shown as default) but can be included manually.

The following is all the `syncy.rsync` configurations.

| Under         | Configuration    | Env      | Cmd      | Description                                                        | Default |
|---------------|------------------|:--------:|:--------:|--------------------------------------------------------------------|---------|
| `syncy.rsync` | `archive`        | &#x2705; | &#x2705; | same as `-a` / `--archive` (equivalent to `-rlptgoD`)              | `True`  |
| `syncy.rsync` | `recursive`      | &#x2705; | &#x2705; | same as `-r` / `--recursive`                                       | `False` |
| `syncy.rsync` | `links`          | &#x2705; | &#x2705; | same as `-l` / `--links`                                           | `False` |
| `syncy.rsync` | `permissions`    | &#x2705; | &#x2705; | same as `-p` / `--permissions`                                     | `False` |
| `syncy.rsync` | `times`          | &#x2705; | &#x2705; | same as `-t` / `--times`                                           | `False` |
| `syncy.rsync` | `group`          | &#x2705; | &#x2705; | same as `-g` / `--group`                                           | `False` |
| `syncy.rsync` | `owner`          | &#x2705; | &#x2705; | same as `-o` / `--owner`                                           | `False` |
| `syncy.rsync` | `devices`        | &#x2705; | &#x2705; | same as `--devices`                                                | `False` |
| `syncy.rsync` | `specials`       | &#x2705; | &#x2705; | same as `--specials`                                               | `False` |
| `syncy.rsync` | `verbose`        | &#x2705; | &#x2705; | same as `-v` / `--verbose`                                         | `1`     |
| `syncy.rsync` | `human_readable` | &#x2705; | &#x2705; | same as `-h` / `--human-readable`                                  | `True`  |
| `syncy.rsync` | `partial`        | &#x2705; | &#x2705; | same as `--partial`                                                | `True`  |
| `syncy.rsync` | `progress`       | &#x2705; | &#x2705; | same as `--progress`                                               | `True`  |
| `syncy.rsync` | `delete`         | &#x2705; | &#x2705; | same as `--delete-before` or `--delete-after` or `--delete-during` | `None`  |
| `syncy.rsync` | `dry`            | &#x2705; | &#x2705; | same as `-n` / `--dry`                                             | `False` |
| `syncy.rsync` | `exclude`        | &#x2705; | &#x274c; | same as `--exclude`                                                | `[]`    |
| `syncy.rsync` | `exclude_from`   | &#x2705; | &#x274c; | same as `--exclude-from`                                           | `[]`    |
| `syncy.rsync` | `include`        | &#x2705; | &#x274c; | same as `--include`                                                | `[]`    |
| `syncy.rsync` | `include_from`   | &#x2705; | &#x274c; | same as `--include-from`                                           | `[]`    |
