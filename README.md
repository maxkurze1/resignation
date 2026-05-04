# re\[sign\]ation

This tool is intended to provide a little convenience for creating digitally signed PDFs on Linux.
For that it is based on a couple of existing tools including:

- [pyHanko](https://github.com/MatthiasValvekens/pyHanko) for the creation of the digital/cryptographic part of the signature
- [typst](https://typst.app/) for the creation of the visual part of the signature

# Documentation

The documentation of this tool can be found [here](https://maxkurze1.github.io/resignation/)

# Why

Most existing tools (at least the dozen I tried) were lacking in one or the other regard. Either
the signatures visual appearance couldn't be configured, or they completely invalidated all existing
signatures when drawing a new one.

Additionally, most of them have been rather inconvenient to use.

# How to use

Before using `resignation` you need to install either [typst](https://typst.app/) and [python](https://www.python.org/)
or [nix](https://nixos.org/) and enable [nix flakes](https://nixos.wiki/wiki/flakes).

After installing these dependencies you have multiple options.

## Nix Flakes

For use with nix, `resignation` provides a flake that can be run directly through nix:

```bash
nix run github:maxkurze1/resignation -- \
  --input document.pdf \
  --output document-signed.pdf \
  --template "github:maxkurze1/resignation?dir=templates/logo"
```

## PyPI

To install the script via pip execute the following command:
(Use a venv if you don't want to install it globally)

```bash
pip install git+https://github.com/maxkurze1/resignation
```

Afterward, you should be able to use the `resignation` command
on its own:

```bash
resignation \
  --input document.pdf \
  --output document-signed.pdf \
  --template "github:maxkurze1/resignation?dir=templates/logo"
```

## Local Development

For local development it is recommended to fetch
all dependencies through nix. This can be done rather
easily by running:

```bash
nix develop
```

Once all dependencies are in place the script can be
run locally as a python module:

```bash
# go into the project root first
python -m resignation.resignation --input some/local/test.pdf
```

