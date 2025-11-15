---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  name: "re[sign]ation"
  # text: "A script to create digital signatures"
  tagline: "A script to create digital signatures"
#   actions:
#     - theme: brand
#       text: Markdown Examples
#       link: /markdown-examples
#     - theme: alt
#       text: API Examples
#       link: /api-examples

# features:
#   - title: Feature A
#     details: Lorem ipsum dolor sit amet, consectetur adipiscing elit
#   - title: Feature B
#     details: Lorem ipsum dolor sit amet, consectetur adipiscing elit
#   - title: Feature C
#     details: Lorem ipsum dolor sit amet, consectetur adipiscing elit
---
This tool is intended to provide a little convenience for creating digitally signed PDFs on Linux.
For that it is based on a couple of existing tools including:

- [pyhanko](https://github.com/MatthiasValvekens/pyHanko) for the creation of the digital/cryptographic part of the signature
- [typst](https://typst.app/) generation of the visual part

# Why

Most existing tools (at least the dozen I tried) were lacking in one or the other regard. Either
the signatures visual appearance couldn't be configured, or they completely invalidated all existing
signatures when drawing the visuals for a new one.

Additionally, most of them have been rather inconvenient to use.

# How to use

To use `resignation` you have multiple options.

## Nix Flakes

For use with nix, `resignation` provides a flake that can be run directly through nix:

```
nix run github:maxkurze1/resignation -- \
  --input document.pdf \
  --output document-signed.pdf \
  --template "github:maxkurze1/resignation?dir=templates/logo"
```

For additional information about the available command line options please refer to [CLI](./cli.md).

## PyPI

To install the script via pip execute the following command:
(Use a venv if you don't want to install it globally)

```
pip install git+https://github.com/maxkurze1/resignation
```

Afterward, you should be able to use the `resignation` command
on its own:

```
resignation \
  --input document.pdf \
  --output document-signed.pdf \
  --template "github:maxkurze1/resignation?dir=templates/logo"
```

