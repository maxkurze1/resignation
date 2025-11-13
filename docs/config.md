---
outline: deep
---

# Config

Most of the command line options can also be moved to a configuration file.
This configuration should be a [TOML](https://toml.io/en/) file.

Here is an example configuration file:

```toml
[Sig1]
certificate = "~/Certificate.p12"
password = "you_dont_have_to_store_it_here"
# ^ but if you do, it is just plain text
# template = "github:maxkurze1/resignation?ref=dev&dir=templates/logo"
template = "github:maxkurze1/resignation?dir=templates/logo"

[Sig1.param]
# name = '[Max Kurze]'
# info = '[#{date}\ another line #{cert_name}]'
logo = 'image("./company.svg")'

[Sig2]
certificate = "~/anotherCert.p12"
password = "plain_text_password"
template = "../templates/logo/"

[Sig2.param]
info = '[#{date}\ Signed by #{cert_name} from #{university}]'
university = '[IDK]'
logo = 'image("./university.svg")'
```

A single configuration can define multiple signature types.
Each signature type contains all the necessary details for the creation
of a specific signature, including the visuals (`template` + `param`) as
well as the cryptographic part (`certificate` + `password`)

Each signature type is referenced by its name.

## Options

### `certificate` {#certificate}

Specifies the certificate file just like [`--certificate`](./cli.md#cli-certificate), exept
that the given path is resolved relative to the configuration file.

### `password` {#password}

Specifies the password to decrypt the certificate file. (see [`--password`](./cli.md#cli-password))

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
