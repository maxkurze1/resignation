---
outline: deep
---

# Config

Most of the command line options can also be moved to a configuration file.
This configuration should be a [TOML](https://toml.io/en/) file.

The config should be located at (`$XDG_CONFIG_HOME` ?: `~/.config`) `/resignation/config.toml`
or explicitly specified on the command line using [`--config`](./cli.md#cli-config)

Here is an example configuration file:

<a id=example></a>

```toml
default = "Sig1"

[Sig1]
certificate = "~/Certificate.p12"
password = "you_dont_have_to_store_it_here"
# ^ but if you do, it is just plain text

# you can select a specific branch with ref=<branch>
# template = "github:maxkurze1/resignation?ref=dev&dir=templates/logo"
template = "github:maxkurze1/resignation?dir=templates/logo"

[Sig1.param]
# name = '[Max Kurze]'
# info = '[#{date}\ another line #{cert_name}]'
logo = 'image("./company.svg")'

[Sig2]
certificate = "~/anotherCert.p12"
template = "../templates/logo/"

[Sig2.param]
info = '[#{date}\ Signed by #{cert_name} from #{university}]'
university = '[IDK]'
logo = 'image("./university.svg")'
```

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
selection prompt of all available signature types of the selected
config file.

Example:

`default = "Sig1"`


## Signature Options

All these options need to be grouped under a common name. E.g. `Sig1` / `Sig2`
as shown in the [example](#example) above.

### `certificate` {#certificate}

Specifies the certificate file just like [`--certificate`](./cli.md#cli-certificate), exept
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

Specifies the template file just like [`--template`](./cli.md#cli-template), exept
that the given path is resolved relative to the configuration file.

### `param` {#param}

Parameters to instantiate the Typst template refer to [templates](./templates.md). (see [`--params`](./cli.md#cli-params))

::: warning
You should not use absolute paths in these parameters as they are all passed to Typst. And Typst
does not like them! Specifically all paths should be relative and inside Typst's working directory.
This working directory is either the config or the `$PWD` of the `resignation` invocation, depending
on whether the `template` was specified through the config or as CLI argument.

Be aware: When setting the template in the config, giving additional params as CLI args should use
(quite unintuitive) links relative to the config.

For more technical infos on this limitation see this [issue](https://github.com/maxkurze1/resignation/issues/3)
:::
