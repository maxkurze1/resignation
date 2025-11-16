# Copyright (C) 2025 Max Kurze <max.kurze@barkhauseninstitut.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 or
# later (see LICENSE.md).

import tempfile
import subprocess
import sys

# def fill_template(template: str, values: dict) -> str:
#   """Replace {{key}} placeholders with corresponding values."""
#   args = ""
#   for key, value in values.items():
#     template = template.replace(f"{{{{{key}}}}}", str(value))
#     args += (f"{key}: {value}, ")

#   template = template.replace("{{..args}}", str(args))

#   return template

def generate_signature_pdf(stamp_pkg, params, cwd) :
  """Build stamp template, replace placeholders, and pipe the result into typst."""

  # with open(signature_template, "r", encoding="utf-8") as f:
  #   content = f.read()
  # #import "{template.name}": stamp
  args = ""
  for key, value in params.items():
    args += f"{key}: {value}, "

  content=f"""
    #import "@resignation/{stamp_pkg['name']}:{stamp_pkg['version']}": stamp

    #set page(width: auto, height: auto, margin: 0pt)
    #stamp({args})
  """

  # filled = fill_template(content, params)

  # Pipe
  process = subprocess.run(
    ["typst", "compile", "-", "-"],
    cwd=cwd,
    input=content.encode("utf-8"),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
  )

  # Print the output (optional)
  stderr = process.stderr.decode()
  if stderr:
    print("Typst produced the following error:", file=sys.stderr)
    print(stderr, file=sys.stderr)
    exit(1)

  # typst pdf as binary stream
  with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
    tmp.write(process.stdout)
    tmp.flush()
    return tmp.name