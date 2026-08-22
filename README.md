# re\[sign\]ation

This tool is intended to provide a little convenience for creating digitally signed PDFs on Linux.
For that it is based on a couple of existing tools including:

- [pyHanko](https://github.com/MatthiasValvekens/pyHanko) for the creation of the digital/cryptographic part of the signature
- [Typst](https://typst.app/) for the generation of the visual part

# Documentation

The documentation of this tool can be found [here](https://maxkurze1.github.io/resignation/)

# Why

Most existing tools (at least the dozen I tried) were lacking in one or the other regard. Either
the signature's visual appearance couldn't be configured, or they completely invalidated all existing
signatures when drawing a new one.

Additionally, most of them have been rather inconvenient to use.

# Features

<img src="./docs/assets/custom_sig_templates.png" alt="Example showing Customizable Visual Signatures" width="40%" align="right">

### Customizable Visual Signatures

Define how signatures should look by using a flexible module system. You can create and host your own
appearance templates, or download existing ones, to adapt the signing experience to your needs.
<br><br>

<img src="./docs/assets/field_selection.png" alt="Example showing Visual Field Selection" width="40%" align="left">
<br>

### Visual Field Selection

Choose from existing signature fields through a visual interface and decide which one should be filled.
<br><br><br><br>

<img src="./docs/assets/custom_field_creation.png" alt="Example showing Interactive Signature Placement" width="40%" align="right">
<br>

### Interactive Signature Placement

Create and position signature fields through an interactive view, specifying exactly where
each signature should appear.
<br><br><br>

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

