#import "@preview/one-liner:0.2.0": fit-to-width

#let overlay_margin = 1pt
#let overlay(img, color) = layout(bounds => {
  let size = measure(img, ..bounds)
  img
  let om = overlay_margin
  place(top + left, move(dx: -om/2, dy: -om/2, block(width: size.width + om, height: size.height + om, fill: color)))
})

#let stamp(height: 0, width: 0, cert_cn: "", info: "", ..args) = grid(
  columns: (1fr, 1fr),
  rows: (1fr),
  gutter: 3pt,
  align: (left + horizon, left + horizon),
  fit-to-width(max-text-size: height - 4pt, text(weight:"bold", cert_cn)),
  place(center + horizon, overlay(image("BI-logo.svg", height:100%), white.transparentize(30%))) +
  fit-to-width(min-text-size:1pt, text(font: "Open Sans", info))
)
