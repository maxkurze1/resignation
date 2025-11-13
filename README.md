# re\[sign\]ation

This tool is intended to provide a little convenience for creating digitally signed PDFs on Linux.
For that it is based on a couple of existing tools including:

- [pyhanko](https://github.com/MatthiasValvekens/pyHanko) for the creation of the digital/cryptographic part of the signature
- [typst](https://typst.app/) for the creation of the visual part of the signature

# Documentation

The documentation of this tool can be found [here](https://maxkurze1.github.io/resignation/)

# Why

Most existing tools (at least the dozen I tried) were lacking in one or the other regard. Either
the signatures visual appearance couldn't be configured, or they completely invalidated all existing
signatures when drawing a new one.

Additionally, most of them have been rather inconvenient to use.

# How to use

To use `resignation` you have multiple options.

## Nix

For use with nix, `resignation` provides a flake that can be used directly like this:

```
nix run github:maxkurze1/resignation -- --input pdfs/mag.pdf --output pdfs/before-svg.pdf --config example/config.toml
```


## PyPI

TODO: work in progress