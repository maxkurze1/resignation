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


from pathlib import Path

def resolve_path(relative: Path, path_str: str) -> Path:
  path = Path(path_str).expanduser()
  if not path.is_absolute():
    path = relative / path
  return path.resolve()

# TODO provide a command to purge all installed stamp packages (at least from the typst directory - nix store probably won't be possible)
# fetch repository using nix and copy it to the typst package directory
def install_typst_stamp(url : str, relative = ".") -> Path:
  # BIG TODO
  url_info = urlparse(url)
  # Linux: $XDG_CACHE_HOME or ~/.cache
  # macOS: ~/Library/Caches -- TODO
  # Windows: %LOCALAPPDATA% -- TODO
  cache_dir = Path(os.getenv("XDG_CACHE_HOME", "~/.cache")).expanduser()

  if not url_info.scheme:
    # url is local path -> use it directly
    path = resolve_path(relative, url)
  else:
    # TODO: this branch is only known to work with github:.. urls
    if shutil.which("nix"):
      process = subprocess.run(
        ["nix", "flake", "prefetch", url, "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
      )
      # fetch a nix flake-url into the nix store and return its local path
      prefetch_info = json.loads(process.stdout.decode())
      path = Path(prefetch_info['storePath']) / prefetch_info["locked"].get("dir", "")
    elif shutil.which("git"):
      from subprocess import DEVNULL
      # fetch with sparse git-clone
      path = cache_dir / "resignation" / url_info.path
      query = parse_qs(url_info.query)
      dir_path = ""
      if 'dir' in query:
        dir_path = query['dir'][0]
      if not path.exists():
        subprocess.run(["git", "clone", "--no-checkout", "--depth=1", "--filter=blob:none", "--no-single-branch", f"https://github.com/{url_info.path}", path], check=True, stdout=DEVNULL)
      subprocess.run(["git", "sparse-checkout", "set", "--no-cone", "/" + dir_path], cwd=path, check=True, stdout=DEVNULL)
      if 'ref' in query:
        subprocess.run(["git", "switch", "-C", query['ref'][0], f"origin/{query['ref'][0]}"], cwd=path, check=True, stdout=DEVNULL)

      subprocess.run(["git", "checkout"], cwd=path, check=True, stdout=DEVNULL)

      path = path / dir_path
    else:
      print(f"Please install either 'git' or 'nix' to fetch remote templates.", file=sys.stderr)
      exit(1)

  typst_config = path / "typst.toml"
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
  typst_repo_dir = cache_dir /  f"typst/packages/resignation/{pkg['name']}/{pkg['version']}"
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

