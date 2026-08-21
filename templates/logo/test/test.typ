#import "../stamp.typ": stamp
// #import "@resignation/resignation-logo:1.0.0": stamp

#set page(width: auto, height: auto, margin: 1cm)

#for (w, h) in (
    (115pt, 19pt),
    (220pt, 40pt),
    (300pt, 20pt),
    ( 60pt, 20pt),
    ( 50pt, 40pt)
  ) [
  #stamp(
    inset: 1pt,
    stroke: (paint: gray, thickness: 0.5pt, dash: "dashed"),
    width: w,
    height: h,
    logo: image("logo.svg"),
    cert_name: [Test Name],
    date: [02.11.2025 16:56:02 +0100],
  )
]

#stamp(
  inset: 1pt,
  stroke: (paint: gray, thickness: 0.5pt, dash: "dashed"),
  width: 100pt,
  height: 20pt,
  logo_opacity: 100%,
  logo: image("logo.svg"),
  cert_name: [Test Name],
  date: [02.11.2025 16:56:02 +0100],
)
