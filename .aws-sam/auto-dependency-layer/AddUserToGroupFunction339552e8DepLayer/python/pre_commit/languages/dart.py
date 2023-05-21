from __future__ import annotations

import contextlib
import os.path
import shutil
import tempfile
from typing import Generator
from typing import Sequence

from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.prefix import Prefix
from pre_commit.util import win_exe
from pre_commit.yaml import yaml_load

ENVIRONMENT_DIR = "dartenv"

get_default_version = lang_base.basic_get_default_version
health_check = lang_base.basic_health_check
run_hook = lang_base.basic_run_hook


def get_env_patch(venv: str) -> PatchesT:
    return (("PATH", (os.path.join(venv, "bin"), os.pathsep, Var("PATH"))),)


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None, None, None]:
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield


def install_environment(
    prefix: Prefix,
    version: str,
    additional_dependencies: Sequence[str],
) -> None:
    lang_base.assert_version_default("dart", version)

    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    bin_dir = os.path.join(envdir, "bin")

    def _install_dir(prefix_p: Prefix, pub_cache: str) -> None:
        dart_env = {**os.environ, "PUB_CACHE": pub_cache}

        with open(prefix_p.path("pubspec.yaml")) as f:
            pubspec_contents = yaml_load(f)

        lang_base.setup_cmd(prefix_p, ("dart", "pub", "get"), env=dart_env)

        for executable in pubspec_contents["executables"]:
            lang_base.setup_cmd(
                prefix_p,
                (
                    "dart",
                    "compile",
                    "exe",
                    "--output",
                    os.path.join(bin_dir, win_exe(executable)),
                    prefix_p.path("bin", f"{executable}.dart"),
                ),
                env=dart_env,
            )

    os.makedirs(bin_dir)

    with tempfile.TemporaryDirectory() as tmp:
        _install_dir(prefix, tmp)

    for dep_s in additional_dependencies:
        with tempfile.TemporaryDirectory() as dep_tmp:
            dep, _, version = dep_s.partition(":")
            if version:
                dep_cmd: tuple[str, ...] = (dep, "--version", version)
            else:
                dep_cmd = (dep,)

            lang_base.setup_cmd(
                prefix,
                ("dart", "pub", "cache", "add", *dep_cmd),
                env={**os.environ, "PUB_CACHE": dep_tmp},
            )

            # try and find the 'pubspec.yaml' that just got added
            for root, _, filenames in os.walk(dep_tmp):
                if "pubspec.yaml" in filenames:
                    with tempfile.TemporaryDirectory() as copied:
                        pkg = os.path.join(copied, "pkg")
                        shutil.copytree(root, pkg)
                        _install_dir(Prefix(pkg), dep_tmp)
                    break
            else:
                raise AssertionError(
                    f"could not find pubspec.yaml for {dep_s}",
                )
