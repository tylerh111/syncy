# Syncy

[![_](https://img.shields.io/pypi/v/syncy)](https://pypi.python.org/pypi/syncy)
[![_](https://img.shields.io/pypi/pyversions/syncy)](https://github.com/tylerh111/syncy)
[![_](https://img.shields.io/pypi/l/syncy)](https://github.com/tylerh111/syncy/blob/main/LICENSE.md)

---

[Syncy](https://github.com/tylerh111/syncy) is a tool for syncing a directory / repository / workspace / etc.

### Origin

When I work with virtual machines, I like to edit the code outside the VM and only build and run within the VM.
This segregation of work is nice because I can keep build and runtime process separate from viewing and modifying the code.
To sync the VM workspace with my actual workspace, I used a script called `sync_repo.sh`.
It was very hacky, and so I wanted to create a more generalized and better written version of that in python.

Sync is the replacement of this `sync_repo.sh` script.
Instead of having semi-hardcoded paths in the script, everything can be configured via a config file.
Now, I have `.syncy.toml` files in each of my repositories that are set up to sync to the repository on the host system.
I simply run `syncy` and everything gets synced as I expect.

### Usage

Syncy is a command line tool that can be called in several ways and configured many ways.
The typical use if to use a configuration file (`.syncy.toml`) to describe the base configurations and use command line arguments to override those configurations.

The following is example config file, named `.syncy.toml`.
It will use the `rsync` command to sync `"path/to/contents"` to the current working directory (the default).

```toml
[syncy]
use = "rsync"
source = "path/to/contents"
```

Syncy will automatically search for this file in the current working directory and run just be running the syncy.

```bash
syncy
```

Configuration options may be specified by environment variables, config files, and command line arguments.
The following is load ordered (low to high): defaults, environment, file, arguments.
Environment variables are the same as the config options in the form `SYNCY_<config>` or `SYNCY_BACKENDS_<backend>_<config>`.
See the help menu for descriptions on available flag.

```bash
syncy --help
```

### Installation

Syncy is available as [`syncy`](https://pypi.python.org/pypi/syncy) on PyPI.

```bash
pip install syncy
```

### Reference

The following is all the `syncy` configurations.

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

### Origin (The *REAL* Story)

Below is the origin of syncy.
It is a tale of dire urgitude.
A tale of superfluous peril.
A tale of unequizical impertiude!

> Part 1: The Golden Age of Virtual Machines!

Virtual machines are awesome.
They can completely encapsulate a project's development and/or runtime environment.
When I'm developing for projects such as this (or having to emulate someone else's environment), this is my go-to solution (yes I know docker exists, but sometimes it's not good enough for replicating environments fully).
I can create virtual machines to my hearts content... until one day I realized something...

> Part 2: Virtual Machines Hold My System Hostage!

Virtual machines are slow.
Well... they are pretty fast, but developing inside the virtual machine can be slow.
And by "developing," I mean running an IDE and modifying code.
Of course, editors like Vscode have extensions for remoting into virtual machines.
Doing this, however, results in only being able to view / change code while the virtual machine is running.
*There must be a solution.*
*I MUST avenge my host system!*

> Part 3: The Dreaded ***`syncy_repo.sh`*** Appears!

To come up with a solution, I created this script called `syncy_repo.sh`.
In my project folder (`/project`), I have all my repos, e.g. `/project/repo`.
I put this script in the project folder, and, from the repo folder I want to sync, I would run `../sync_repo.sh`.
The magical script would be able to parse the correct repo directory and then sync (using rsync) with the source directory (with the same directory structure).
Now, I can edit my code on my host system, but sync, build, and run it on the virtual system.

GREAT... or so I thought.

See, the level of hackiness that went into that script is far beyond and boundary one should cross when creating a quick solution to a problem.
There were partially hardcoded paths, weird default settings (e.g. change the owner and group), having a truly gargantuan list of excluded patterns that were hard to modify (due to bash).

> Part 4: Enlightenment and Embrace

Goal: create a python script that can generate the correct rsync command from a config file.

*Couple years later...*

Here we are!
Syncy is essentially a configurable rsync.
But it's more than that.
I wanted to have support for many backends, not just rsync.
Now, instead of having this weirdly constructed script that only works for one project, I can configure each repository and simply run `syncy` and...

> It just works! (Todd Howard)
