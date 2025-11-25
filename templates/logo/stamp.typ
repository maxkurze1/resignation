#import "@preview/one-liner:0.2.0": fit-to-width

#let overlay_margin = 1pt
#let overlay(img, color) = layout(bounds => {
  let size = measure(img, ..bounds)
  img
  let om = overlay_margin
  place(top + left, move(dx: -om/2, dy: -om/2, block(width: size.width + om, height: size.height + om, fill: color)))
})

#set image(height: 100%)

#let stamp(
    /* required */
    height: 0pt,
    width: 0pt,
    rotation: 0deg,
    /* optional */
    cert_name: [],
    date: [],
    logo: [],
    inset: 2pt,
    stroke: none,
    logo_opacity: 30%,
    ..args) = {
  let args = args.named();
  // typst does not support arguments with default values that depend on other args
  // (i.e. its not possible to write 'name: [#cert_name]' in the arg list)
  // but we can emulate them:
  let name = args.at("name", default: cert_name);
  let info = args.at("info", default: [Digitally signed by #name\ Date: #date]);
  rotate(rotation,
    box(
      inset: inset,
      height: height,
      width: width,
      stroke: stroke,
      grid(
        columns: (1fr, 1fr),
        rows: (1fr),
        gutter: 3pt,
        align: (center + horizon, left + horizon),
        fit-to-width(max-text-size: height - 4pt, text(weight:"bold", name)),
        /* the logo is centered behind the info text */
        place(center + horizon, overlay(logo, white.transparentize(logo_opacity))) +
        fit-to-width(min-text-size:1pt, text(font: "Open Sans", info))
        // TODO make sure font is available?
      )
    ),
    reflow: true
)}
