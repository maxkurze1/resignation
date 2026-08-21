---
outline: deep
---

# Config

Most of the command line options can also be moved to a configuration file.
This configuration should be a [TOML](https://toml.io/en/) file.

The config needs to be explicitly specified on the command line using [`--config`](./cli.md#cli-config)
or should be located at:

::: code-group

``` [Linux]
${XDG_CONFIG_HOME:-~/.config}/resignation/config.toml
```

``` [MacOS]
~/Library/Application Support/resignation/config.toml
```

``` [Windows]
%APPDATA%/resignation/config.toml
```

:::


Here is an example configuration file:

<a id=example></a>

```toml
default = "Sig1"

[Sig1]
certificate = "~/Certificate.p12"
password = "you_dont_have_to_store_it_here"
# ^ but if you do, it is just plain text

# You can select a specific branch with ref=<branch>
# template = "github:maxkurze1/resignation?ref=dev&dir=templates/logo"
template = "github:maxkurze1/resignation?dir=templates/logo"

# Default name of the saved document. Placeholders {name}/{ext}/{dir}/{input}
# refer to the input file, so this is an easy way to add a suffix or prefix.
output = "{dir}/{name}-signed{ext}"

[Sig1.param]
name = '[Max Kurze]'
logo = 'image("./company.svg")'
info = '[#{date}\ name: #{name}]'
# You can refer to other parameters using the '{ ... }'
# syntax - but keep in mind that, by convention,
# all parameters are typst primitives. Thus they should be
# used from within "code-mode"

[Sig2]
certificate = "~/anotherCert.p12"
template = "../templates/logo/"
# templates can also be stored locally

[Sig2.param]
info = '[#{date}\ Signed by #{cert_name} from #{university}]'
university = '[IDK]'
logo = 'image("./university.svg")'
date = '[{shell: date "+%A, %d %B %Y %H:%M"}]'
# Even arbitrary shell commands are supported by a '{shell: ... }'
# syntax. Again, keep in mind to wrap them into a typst content
# block '[ ... ]'.
```

<a id=sig-types></a>

A single configuration can define multiple _signature types_ (here `Sig1` and `Sig2`).
Each signature type contains all the necessary details for the creation
of a specific signature, including the visuals (`template` + `param`) as
well as its cryptographic part (`certificate` + `password`).
Each signature type is referenced by its name (see [`default`](#default) and [`--sig`](./cli.md#cli-sig)).

## General Options

### `default` {#default}

Specifies the name of the signature type which should be used with
this config if no name is given explicitly using [`--sig`](./cli.md#cli-sig).

If neither `default` nor `--sig` is present, resignation will show a
selection prompt of all available signature types in config file.

Example:

`default = "Sig1"`


## Signature Options

All these options need to be grouped under a common name. E.g. `Sig1` / `Sig2`
as shown in the [example](#example) above.

### `certificate` {#certificate}

Specifies the certificate file just like [`--certificate`](./cli.md#cli-certificate), except
that the given path is resolved relative to the configuration file.

### `password` {#password}

Specifies the password to decrypt the certificate file. (see [`--password`](./cli.md#cli-password))

::: warning
This option is deprecated in favor of the new behavior which saves the
password in the system's keyring. It is only kept for people which do
not have/use a keyring service on their operating system.
:::

::: danger
If you enter your password here, it will be saved in plain text on your hard drive.
This may expose your password to security risks.

To avoid potential password theft, you can leave this option unset — you will then be prompted to enter your password each time a signature is created.
:::

### `template` {#template}

Specifies the template file just like [`--template`](./cli.md#cli-template), except
that the given path is resolved relative to the configuration file.

### `output` {#output}

Specifies a default name (or path) for the saved document. This value is used as
the pre-filled default of the output prompt, so it can still be edited before saving.
If unset, the output defaults to the input file path (as before).

The value is a template that may refer to the input file through the following
placeholders:

| Placeholder | Meaning                            |
| ----------- | ---------------------------------- |
| `{input}`   | full input path                    |
| `{dir}`     | input directory                    |
| `{name}`    | input file name without extension  |
| `{ext}`     | extension (including leading dot)  |

This makes it easy to add a prefix or a suffix to the input name:

```toml
# suffix, e.g. "document.pdf" -> "document-signed.pdf"
output = "{dir}/{name}-signed{ext}"

# prefix, e.g. "document.pdf" -> "signed-document.pdf"
output = "{dir}/signed-{name}{ext}"

# or a fixed default name / location
output = "~/signed/{name}{ext}"
```

The corresponding command-line option is [`--output`](./cli.md#cli-output), which
takes precedence and is used directly (without prompting).

### `param` {#param}

Parameters to instantiate the Typst template with. These parameters are (for the most part)
highly specific to the stamp template you are using. Thus, you should search for
their specification in the documentation of your template. (see [here](https://github.com/maxkurze1/resignation/tree/main/templates) for the default stamps)

For more information — also regarding the few template agnostic parameters — refer to [templates](./templates.md).
The corresponding command-line option for `param` is [`--params`](./cli.md#cli-params).

::: warning
You should not use absolute paths in these parameters as they are all passed to Typst. And Typst
does not like them! Specifically all paths should be relative and inside Typst's working directory.
This working directory is either the config or the `$PWD` of the `resignation` invocation, depending
on whether the `template` was specified through the config or as CLI argument.

Be aware: When setting the template in the config and additionally giving `--params` via the CLI, then
these CLI parameters should use (quite counter-intuitive) links relative to the config.

For more technical infos on this limitation see this [issue](https://github.com/maxkurze1/resignation/issues/3)
:::
