---
# https://vitepress.dev/reference/default-theme-home-page
layout: home
title: ""
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

- [pyHanko](https://github.com/MatthiasValvekens/pyHanko) for the creation of the digital/cryptographic part of the signature
- [Typst](https://typst.app/) for the generation of the visual part

::: tip Looking for all the details?
The [**Reference**](./cli.md) documentation describes every available option:
the [command line interface](./cli.md), the [config file](./config.md) and the
[stamp templates](./templates.md).
:::

# Why

Most existing tools (at least the dozen I tried) were lacking in one or the other regard. Either
the signature's visual appearance couldn't be configured, or they completely invalidated all existing
signatures when drawing the visuals for a new one.

Additionally, most of them have been rather inconvenient to use.

# Features


<div class="flex lg:flex-row flex-col items-center justify-center lg:gap-16 mb-16">

<div class="sm:max-w-136">

### Customizable Visual Signatures

Define how signatures should look by using a flexible module system. You can create and host your own
appearance templates, or download existing ones, to adapt the signing experience to your needs.

</div>

![](./assets/custom_sig_templates.png){.max-w-104! .w-full}

</div>



<div class="flex lg:flex-row-reverse flex-col items-center justify-center lg:gap-16 mb-16">

<div class="sm:max-w-104">

### Visual Field Selection

Choose from existing signature fields through a visual interface and decide which one should be filled.

</div>

![](./assets/field_selection.png){.max-w-128! .w-full}

</div>


<div class="flex lg:flex-row flex-col items-center justify-center lg:gap-16 mb-16">

<div class="sm:max-w-96">

### Interactive Signature Placement

Create and position signature fields through an interactive view, specifying exactly where
each signature should appear.

</div>

![](./assets/custom_field_creation.png){.max-w-112! .w-full}

</div>

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

# Where to Go From Here

Once you have `resignation` up and running, you can find all the advanced
configuration and customization options in the reference documentation:

- [**Command Line Interface**](./cli.md) — all command line options and environment variables
- [**Config Options**](./config.md) — how to move those options into a config file
- [**Templates**](./templates.md) — how to write and use your own visual stamp templates
