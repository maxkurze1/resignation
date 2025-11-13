---
outline: deep
---

# Command Line Interface

## Options

### `-i` / `--input` {#cli-input}

Specifies the path to the input PDF.
If omitted, the path is prompted.

Example:

`--input "./here/is/my/document.pdf"`

### `-o` / `--output` {#cli-output}

Specifies the path to the outupt PDF.
If omitted, the path is prompted.

Example:

`--output "./put/it/here/document-sined.pdf"`

### `-t` / `--template` {#cli-template}

This option specifies the Typst template which is used to generate the visual
part of the signature.

The template should be given as a directory containing a valid Typst package.
This directory may either be a local path or a [nix-flake-input-style](https://nix.dev/manual/nix/2.28/command-ref/new-cli/nix3-flake.html#types)
GitHub reference.

If omitted, the template's location is loaded from the [config](./config.md) or prompted.

::: info
When using a GitHub reference it is necessary to specify the exact path to the Typst
package directory as `?dir=<path>`
:::

Examples:

`--template ./some/directory/`<br>
`--template="~/here/"`<br>
`-t "github:maxkurze1/resignation?dir=templates/logo"`

For additional information about the template process refer to [templates](./templates.md).

### `-p` / `--param` / `--params` {#cli-params}

Template specific parameters, refer to the documentation of your template.
These parameters are given as key-value pairs (in the form `<key>=<value>`).
The provided values need to be valid Typst objects, see [templates](./templates.md#parameters)

This flag accepts multiple parameters at once, but it can also be invoked multiple times.

Examples:

`--params info=[Hello] name=[#{cert_name}] inset=3pt`<br>
`--param date=[Today] --param info=[Date: #{date}]`

### `--cert` / `--certificate` {#cli-certificate}

The path to the PKCS 12 certificate.

If omitted, the path is either loaded from the [config](./config.md) or prompted.

Example:

`--cert "~/Certificate.p12"`

### `--pass` / `--password` {#cli-password}

Via this flag the certificate's password may be specified.

If not present the password is loaded from the [config](./config.md) or prompted.

### `-c` / `--config` {#cli-config}

Specifies the path to the signature config.

If not present, the config is searched at `$XDG_CACHE_HOME/resignation/config.toml` and
`~/.config/resignation/config.toml`.

This configuration file may provide default for various command line option.
For more information refer to [config](./config.md).

Example:

`--config "~/.config/resignation/config.toml"`

## Environment Variables

Additionally, resignation also can be configured through environment variables.

### `RESIGNATION_PARAMS` {#env-params}

The `RESIGNATION_PARAMS` variable can be used to provide additional
template parameters for the Typst invocation.
It should contain these parameters separated by colons `:` in the form of
key-value pairs `<key>=<value>`.

`RESIGNATION_PARAMS="name=[My Name]:info=[Hello\ Date: #{date}]"`

Note that the given `<value>`s still need to be valid Typst objects.
Thus, they are wrapped into content blocks `[ ... ]` here.

The precedence of parameters given through this environment variable is right
above the ones from the configuration file and below the parameters given on
the command line.