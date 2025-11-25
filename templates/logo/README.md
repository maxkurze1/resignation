# Logo stamp

This template can be used to create stamps with logos like:

![preview of stamps with logos](./test/test.png)


## Params

### stroke

Typst stroke options to outline the whole signature.
(default: `none`)

Example

`stroke='(paint: gray, thickness: 0.5pt, dash: "dashed")'`

### inset

Padding between the signatures box and its content.
(default: `2pt`)

### name

The name that is shown on the left half of the signature.
(default: `{cert_name}`)

### info

The info text that is shown on the right side of the signature.
(default: `[Digitally signed by #{name}\ Date: #{date}]`)

### logo

The content that is shown behind the right half of the signature.
(default: `[]`)

Example:

`logo='image("./TUD-logo-new.svg")'`


### logo_opacity

Opacity of the background logo.
(default: `30%`)

Example:

`logo_opacity='50%'`
