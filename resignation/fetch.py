# Copyright (C) 2025 Max Kurze <max.kurze@barkhauseninstitut.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 or
# later (see LICENSE.md).

import tempfile
import subprocess
import os
import io
import stat
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import tomllib
import json
import shutil
import platform

def resolve_path(relative: Path, path_str: str) -> Path:
  path = Path(path_str).expanduser()
  if not path.is_absolute():
    path = relative / path
  return path.resolve()

# TODO provide a command to purge all installed stamp packages (at least from the typst directory - nix store probably won't be possible)
# fetch repository using nix and copy it to the typst package directory
def install_typst_stamp(url : str, relative = ".", refresh = False, offline = False) -> Path:
  # BIG TODO
  url_info = urlparse(url)
  cache_dir = {
    'Linux': Path(os.getenv("XDG_CACHE_HOME", "~/.cache")).expanduser(),
    'Darwin': Path("~/Library/Caches").expanduser(),
    'Windows': Path(os.path.expandvars("%LOCALAPPDATA%")),
  }[platform.system()]

  query = parse_qs(url_info.query)
  dir_path = ""
  if 'dir' in query:
    dir_path = query['dir'][0]
  if not url_info.scheme:
    # url is local path -> use it directly
    path = resolve_path(relative, url)
  else:
    # TODO: this branch is only known to work with github:.. urls
    try:
      if shutil.which("nix"):

        nix_fetch_cmd = ["nix", "flake", "prefetch", url, "--json"]
        if refresh:
          nix_fetch_cmd.append("--refresh")
        if offline:
          nix_fetch_cmd.append("--offline")

        process = subprocess.run(
          nix_fetch_cmd,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          text=True,
          check=True
        )
        # fetch a nix flake-url into the nix store and return its local path
        prefetch_info = json.loads(process.stdout)
        path = Path(prefetch_info['storePath'])/dir_path
      elif shutil.which("git"):
        # TODO support refresh and offline!
        from subprocess import DEVNULL, PIPE
        # fetch with sparse git-clone
        path = cache_dir/"resignation"/url_info.path
        if not path.exists():
          if not offline:
            print(f"Cloning stamp template repository (github:{url_info.path}) into {path}")
            subprocess.run(["git", "clone", "--no-checkout", "--depth=1", "--filter=blob:none", "--no-single-branch", f"https://github.com/{url_info.path}", path], check=True, stdout=DEVNULL, stderr=PIPE, text=True)
          else:
            print(f"Template repository (github:{url_info.path}) not available offline!", file=sys.stderr)
            exit(1)
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone", "/" + dir_path], cwd=path, check=True, stdout=DEVNULL, stderr=PIPE, text=True)

        ref = ''
        if 'ref' in query:
          ref = f"origin/{query['ref'][0]}"
        else:
          ref = f"origin/HEAD"

        # check if specified branch (ref) is known locally
        rev_parse = subprocess.run(["git", "rev-parse", "--verify", ref], cwd=path, stdout=DEVNULL, stderr=DEVNULL, text=True)
        ref_available = rev_parse.returncode == 0

        if refresh or (not ref_available and not offline):
          try:
            subprocess.run(["git", "fetch", "--depth=1", "origin", query['ref'][0]], cwd=path, check=True, stdout=DEVNULL, stderr=PIPE, text=True)
          except subprocess.CalledProcessError as e:
            print(f"Failed to fetch specified branch of the template repository.", file=sys.stderr)
            print(f"This is likely caused by a typo in the branch name: '{query['ref'][0]}'", file=sys.stderr)
            print(f"Git error:\n{e.stderr}", file=sys.stderr)
            exit(1)

        subprocess.run(["git", "reset", "--hard", ref], cwd=path, check=True, stdout=DEVNULL, text=True)

        path = path/dir_path
      else:
        print(f"Please install either 'git' or 'nix' to fetch remote templates.", file=sys.stderr)
        exit(1)
    except subprocess.CalledProcessError as e:
      print(f"Failed to fetch template:\n{e.stderr}", file=sys.stderr)
      exit(1)

  typst_config = path/"typst.toml"
  if not typst_config.exists():
    print(f"Typst package config {typst_config} is missing.", file=sys.stderr)
    exit(1)

  with open(typst_config, "rb") as f:
    pkg_data = tomllib.load(f)

  if not 'package' in pkg_data:
    print(f"Typst package config (typst.toml) is missing required table 'package'.", file=sys.stderr)
    exit(1)

  pkg = pkg_data['package']

  if not 'name' in pkg or not 'version' in pkg or not 'entrypoint' in pkg:
    print(f"Typst package config (typst.toml) is missing required fields. (name/version/entrypoint)", file=sys.stderr)
    exit(1)

  # copy typst package to local typst package cache
  typst_repo_dir = cache_dir/"typst"/"packages"/"resignation"/pkg['name']/pkg['version']
  if typst_repo_dir.exists():
    # change mode because these files are copied from the nix store and therefore read-only
    for root, dirs, files in os.walk(typst_repo_dir):
      for name in dirs + files + [""]:
        full_path = os.path.join(root, name)
        mode = os.stat(full_path).st_mode
        os.chmod(full_path, mode | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    shutil.rmtree(typst_repo_dir)

  shutil.copytree(path, typst_repo_dir, dirs_exist_ok=True)

  return pkg

