#import "../stamp.typ": stamp

#set page(width: auto, height: auto, margin: 1cm)

#for (w, h) in (
    (115pt, 19pt),
    (220pt, 40pt),
    (300pt, 20pt),
    ( 60pt, 20pt)
  ) [
  #rotate(0deg, box(
    inset: 1pt,
    height: h,
    width: w,
    stroke: (paint: gray, thickness: 0.5pt, dash: "dashed"),
    stamp(
      width: w,
      height: h,
      logo: image("logo.svg"),
      cert_name: [Test Name],
      info: [Digitally signed by Test Name\ Date: 02.11.2025 16:56:02 +0100]
    )
  ), reflow: true)
]