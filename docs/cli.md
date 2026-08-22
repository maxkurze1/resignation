---
outline: deep
---

# Command Line Interface

None of these command line options are mandatory,
all of them can be left out and the script will ask
for all the details that it needs.

## Options

### `-i` / `--input` {#cli-input}

Specifies the path to the input PDF.
If omitted, the path is prompted.

Example:

`--input "./here/is/my/document.pdf"`

### `-o` / `--output` {#cli-output}

Specifies the path to the output PDF.
If omitted, the path is prompted (using the config's [`output`](./config.md#output)
template as the default if present).

The value may use the same `{name}`/`{ext}`/`{dir}`/`{input}` placeholders as the
config's [`output`](./config.md#output) option, which refer to the input file.

Example:

`--output "./put/it/here/document-signed.pdf"`

`--output "{dir}/{name}-signed{ext}"`

### `--new-field` {#cli-new-field}

Specify the page + position of a new signature field.
This will cause this new field to be created and
immediately selected for signing.

The field's position may be specified either using
the upper-left and lower-right corners or using the
upper-left corner together with a width and height.

Relative values (width and height) are distinguished by
a `+` prefix.

Format:

`<page>/<x1>,<y1>,<x2>,<y2>` or<br>
`<page>/<x>,<y>,+<width>,+<height>`

Examples:

`--new-field 0/100,50,200,90`<br>
`--new-field 1/100,50,+100,+40`

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

### `--offline` {#cli-offline}

Try to do everything offline, and emit an error if a resource is not available.

### `--refresh` {#cli-refresh}

Try to refresh resources that are fetched from the network (e.g. templates).
In case the network is unavailable, fall back to the cached version instead.

### `-p` / `--param` / `--params` {#cli-params}

Template specific parameters, refer to the documentation of your template. (see [here](https://github.com/maxkurze1/resignation/tree/main/templates) for the default stamps)

These parameters are given as key-value pairs (in the form `<key>=<value>`).
The provided values need to be valid Typst objects, see [templates](./templates.md#parameters).

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

If not present the password is loaded from the [config](./config.md), keyring or prompted.

::: warning
The usage of this flag is discouraged, please use [`--ask`](#cli-ask) instead, to
prevent that the password is captured in your shell's history.
:::

Example:

`--password "tHis!sMyPa22w0rd"`

### `-a` / `--ask` {#cli-ask}

This flag disables the keyring lookup and instead always prompts the user for the
certificate's password. It is a boolean flag and does not need an argument.

Example:

`--ask`

### `-c` / `--config` {#cli-config}

Specifies the path to the signature config.

If not present, the config is searched at `$XDG_CACHE_HOME/resignation/config.toml` and
`~/.config/resignation/config.toml`.

This configuration file may provide defaults for various command line options.
For more information refer to [config](./config.md).

Example:

`--config "~/.config/resignation/config.toml"`

### `-s` / `--sig` {#cli-sig}

Specifies the name of the [_signature type_](./config.md#sig-types) that should be used (only necessary if
the config contains multiple signature types). If left unspecified, the config's
[`default`](./config.md#default) will be used or the user will be prompted.

Example:

`--sig "Sig1"`

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