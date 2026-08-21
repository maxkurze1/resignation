#import "@preview/one-liner:0.2.0": fit-to-width

// Fit `body` into the surrounding box, maxing the font size while respecting
// the width+height limitation (uses text wrapping)
#let fit-to-box(
  body,
  min-size: 1pt,
  max-size: 720pt,
  tolerance: 0.25pt,
  align: left + horizon,
) = layout(bounds => {
  let (width: w, height: h) = bounds

  // Does `body` fit the box when rendered at `size`, wrapped to width `w`?
  let fits(size) = {
    // Capping width to force natural line wrapping
    // When the text fits, `.width` reports the true
    // widest-line width; a line (e.g. an unbreakable word) too wide to wrap
    // makes `.width` clamp to exactly `w`, so `< w` rejects that overflow.
    let m = measure(text(size: size, body), width: w)
    m.height <= h and m.width < w
  }

  // Binary search the largest feasible size. `fits` is monotonic in `size`
  // (both height and widest-line width grow with size), so this converges.
  let lo = min-size
  let hi = max-size
  while hi - lo > tolerance {
    let mid = (lo + hi) / 2
    if fits(mid) { lo = mid } else { hi = mid }
  }

  set text(size: lo)
  set par(justify: false)
  std.align(align, block(width: w, body))
})

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
  let left_side = args.at("left", default: name)
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
        fit-to-box(text(weight:"bold", left_side), max-size: height - 4pt, align: center + horizon),
        /* the logo is centered behind the info text */
        place(center + horizon, if logo_opacity == 100% { logo } else { overlay(logo, white.transparentize(logo_opacity)) }) +
        fit-to-width(min-text-size:1pt, text(font: "Open Sans", info))
        // TODO make sure font is available?
      )
    ),
    reflow: true
)}
