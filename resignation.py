#!/usr/bin/env python3

import fitz  # PyMuPDF
from InquirerPy import prompt
from InquirerPy import inquirer
from InquirerPy.validator import PathValidator
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.base.control import Choice

def get_page_sig_fields(page):
  return list(filter(lambda w: w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE, page.widgets()))
def get_empty_page_sig_fields(page):
  return list(filter(lambda w: not w.is_signed, get_page_sig_fields(page)))

def show_annotated_page(doc, idx):
  # count widgets of prior pages
  counter = 0
  for i in range(idx):
    counter += len(get_empty_page_sig_fields(doc[i]))

  page = doc[idx]
  # print(f"page rotation {page}: {page.rotation}") # page's rotation clockwise (always multiple of 90)
  for widget in page.widgets():
    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
      # print(counter, widget.field_name, ":", widget.is_signed)
      if not widget.is_signed:
        page.draw_rect(widget.rect, color=[1.0, 0.0, 0.0], fill=[1.0,1.0,1.0], fill_opacity=0.8, overlay=True)
        page.insert_textbox(widget.rect, f"{counter}", overlay=True, color=[1.0, 0.0, 0.0], align=fitz.TEXT_ALIGN_CENTER, rotate=page.rotation)
        # print("w/h", widget.rect.width, widget.rect.height)
        counter += 1
  page_img = page.get_pixmap(dpi=300).pil_image()
  page_img.show()

def page_field_of_idx(doc, idx):
  # count widgets of prior pages
  for page in doc:
    sig_fields = get_empty_page_sig_fields(page)
    if idx >= len(sig_fields) :
      idx -= len(sig_fields)
      continue
    return page, sig_fields[idx]


from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

def get_opt(lst, index, default=None):
  return lst[index].value if -len(lst) <= index < len(lst) else ""

def extract_name_from_pk12(pk12_path, password: str | None = None) -> str | None:
  """
  Extract subject information from a PKCS#12 (.p12/.pfx) certificate.
  """
  # Read PKCS#12 file
  with open(pk12_path, "rb") as f:
    pk12_data = f.read()

  # Load private key and certificate
  private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
    pk12_data,
    password if password else None,
    backend=default_backend()
  )

  if not certificate:
    print("No certificate found in the PKCS#12 file.")
    return None

  return {
    "cert_name":       f"[{get_opt(certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME      ),0)}]",
    "cert_country":    f"[{get_opt(certificate.subject.get_attributes_for_oid(NameOID.COUNTRY_NAME     ),0)}]",
    "cert_org":        f"[{get_opt(certificate.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME),0)}]",
    "cert_surname":    f"[{get_opt(certificate.subject.get_attributes_for_oid(NameOID.SURNAME          ),0)}]",
    "cert_given_name": f"[{get_opt(certificate.subject.get_attributes_for_oid(NameOID.GIVEN_NAME       ),0)}]",
    "cert_title":      f"[{get_opt(certificate.subject.get_attributes_for_oid(NameOID.TITLE            ),0)}]",
    "cert_initials":   f"[{get_opt(certificate.subject.get_attributes_for_oid(NameOID.INITIALS         ),0)}]",
    "cert_pseudonym":  f"[{get_opt(certificate.subject.get_attributes_for_oid(NameOID.PSEUDONYM        ),0)}]",
    "cert_email":      f"[{get_opt(certificate.subject.get_attributes_for_oid(NameOID.EMAIL_ADDRESS    ),0)}]",
  }

from pyhanko import stamp
from pyhanko.sign import fields, signers
from pyhanko.pdf_utils import layout
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

import io
import tempfile
import subprocess

from datetime import datetime

def get_formatted_date():
  now = datetime.now().astimezone()
  return now.strftime("%d.%m.%Y %H:%M:%S %z")

def fill_template(template: str, values: dict) -> str:
  """Replace {{key}} placeholders with corresponding values."""
  args = ""
  for key, value in values.items():
    template = template.replace(f"{{{{{key}}}}}", str(value))
    args += (f"{key}: {value}, ")

  template = template.replace("{{..args}}", str(args))

  return template

def generate_signature_pdf(template, template_params) :
  """Read a signature style, replace templates, and pipe the result into typst."""

  # with open(signature_template, "r", encoding="utf-8") as f:
  #   content = f.read()
  content=f"""
    #import "{template.name}": stamp
    #set page(width: auto, height: auto, margin: 0pt)
    #rotate({{{{rotation}}}}, box(
      inset: 1pt,
      height: {{{{height}}}},
      width: {{{{width}}}},
      stamp({{{{..args}}}})
    ), reflow: true)
  """

  filled = fill_template(content, template_params)

  # Pipe
  process = subprocess.run(
    ["typst", "compile", "-", "-"],
    cwd=template.parent,
    input=filled.encode("utf-8"),
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

from pathlib import Path

# resolve paths in the config relative to the config
def resolve_path(config_dir: Path, path_str: str) -> Path:
  path = Path(path_str).expanduser()
  if not path.is_absolute():
    path = config_dir / path
  return path.resolve()

import json
from urllib.parse import urlparse, parse_qs

def fetch_url(url : str, relative = ".") -> Path:
  # BIG TODO
  url_info = urlparse(url)
  if not url_info.scheme:
    # url is local path -> use it directly
    return resolve_path(relative, url) / "template.typ"
  else:
    process = subprocess.run(
      ["nix", "flake", "prefetch", url, "--json"],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE
    )
    # fetch a nix flake-url into the nix store and return its local path
    prefetch_info = json.loads(process.stdout.decode())
    return Path(prefetch_info['storePath']) / prefetch_info["locked"].get("dir", "") / "template.typ"

  # url_dir = urlparse('github:maxkurze1/resignation?dir=templates/logo-template')
  # parse_qs(url_dir.query)['dir'][0] -> 'templates/logo-template'





# TODO from importlib.metadata import version
import argparse
import os
import sys
import tomllib  # built-in since Python 3.11

def main():
  parser = argparse.ArgumentParser(prog='resignation', description="digital signature creator")
  parser.add_argument("-i", "--input", help="input PDF file path")
  parser.add_argument("-o", "--output", help="output PDF file path")
  parser.add_argument("--password", help="password of certificate")
  parser.add_argument("--certificate", help="path to certificate")
  parser.add_argument("-t", "--template", help="nix-url of stamp-template")
  parser.add_argument("-c", "--config", help="path to config [':'<signature_name>]")
  parser.add_argument("-p", "--param", action='append', help="template parameter", nargs='*')
  # TODO parser.add_argument('--version', action='version', version=f"%(prog)s {version("resignation")}", help="Show version and Git commit hash")
  args = parser.parse_args()

  # validate passed params
  cli_template_params = {}
  if args.param:
    for p in [x for l in args.param for x in l]:
      if "=" in p:
        key, value = p.split("=", 1)
        # print("k/v", key, value)
        cli_template_params[key] = value
      else:
        print(f"Error: invalid input ({p}) - params need to be key value pairs given in the form '<key>=<value>'.", file=sys.stderr)
        sys.exit(1)

  # check / prompt for input path
  if args.input is not None:
    file_in = args.input
  else:
    file_in = inquirer.filepath(
      message="Enter PDF file to sign:",
      validate=PathValidator(is_file=True, message="Input is not a file"),
    ).execute()

  # process PDF for signature fields
  doc = fitz.open(file_in)
  page_choices = []
  for i, page in enumerate(doc):
    page_choices.append(
      Choice(
        value=i,
        name=f"page {i}: {len(get_empty_page_sig_fields(page))}/{len(get_page_sig_fields(page))}"
      ),
    )

  # loop to select page / signature field on page
  while True:
    prompt = inquirer.select(
      message="On which page do you want to sign? (press 'p' to preview page)\n  (empty fields / total fields):",
      choices=page_choices,
      default=None,
      vi_mode=True,
    )

    @prompt.register_kb("p")
    def _handle_preview(event):
      show_annotated_page(doc, prompt.result_value)

    page_idx = prompt.execute()
    min_idx = 0
    for i in range(page_idx):
      min_idx += len(get_empty_page_sig_fields(doc[i]))
    max_idx = min_idx + len(get_empty_page_sig_fields(doc[page_idx])) - 1

    prompt = inquirer.number(
      message=f"Select which field to sign [{min_idx} - {max_idx}] (press 'p' to preview page):",
      min_allowed=min_idx,
      max_allowed=max_idx,
      validate=EmptyInputValidator(),
      vi_mode=True,
    )

    @prompt.register_kb("p")
    def _handle_preview(event):
      show_annotated_page(doc, page_idx)

    @prompt.register_kb("escape")
    def _handle_exit(event):
      prompt.application.exit()

    field_idx_opt = prompt.execute()
    if field_idx_opt:
      field_idx = int(field_idx_opt)
      break

  # page and idx was selected
  page, field = page_field_of_idx(doc, field_idx)
  field_name = field.field_name

  # next: collect certificate path + password + signature template
  cert_path = None
  password = None
  template_path = None
  config_params = {}

  # load all values from config if available
  if args.config:
    sig_conf = str(args.config).split(':')
    sig_conf_dir = Path(sig_conf[0]).resolve().parent

    with open(Path(sig_conf[0]).expanduser(), "rb") as f: # must open in binary mode
      data = tomllib.load(f)

    sig_conf_d = None
    if len(sig_conf) > 1:
      sig_conf_d = data[sig_conf[1]]
    else:
      # try to load the first signature in config
      # TODO maybe consider opening a dialog here that lets the user choose one
      key = next(iter(data), None)
      if key:
        sig_conf_d = data[key]
      else:
        print(f"Warning: Signature config file does not contain entries.", file=sys.stderr)

    if sig_conf_d:
      cert_path = resolve_path(sig_conf_dir, sig_conf_d['certificate']) if 'certificate' in sig_conf_d else None
      password = sig_conf_d['password'].encode() if 'password' in sig_conf_d else None
      template_path = resolve_path(sig_conf_dir, sig_conf_d['template']) if 'template' in sig_conf_d else None # todo support nix-paths also in the config
      config_params = sig_conf_d['param'] if 'param' in sig_conf_d else {}

  # if value are given on the command line they take precedence
  if args.template:
    # if different template is given on the command line ignore template + params of config
    template_path = fetch_url(args.template)
    config_params = {}
  if args.password:
    password = args.password.encode()
  if args.certificate:
    cert_path = Path(certificate).resolve()

  # if some values are still missing -> prompt user
  if not cert_path:
    cert_path = Path(inquirer.filepath(
      message="Select Certificate file:",
      validate=PathValidator(is_file=True, message="Input is not a file"),
    ).execute()).expanduser().resolve()

  # prompt password
  if not password:
    password = inquirer.secret(
      message=f"Enter password (for {cert_path}):",
      transformer=lambda _: "[hidden]",
    ).execute().encode()

  if not template_path:
    # if config does not contain template then also ignore params of config
    config_params = {}
    template_path = fetch_url(inquirer.text(message="Enter signature template url:").execute())

  cert_data = extract_name_from_pk12(cert_path, password)
  date = get_formatted_date()

  # TODO if rotation is set in template it is not clear if the box dimensions should be rotatet too or only the content?
  if page.rotation == 90 or page.rotation == 270:
    field_wdt = field.rect.height
    field_hgt = field.rect.width
  else:
    field_wdt = field.rect.width
    field_hgt = field.rect.height

  template_data = {
    "rotation": f"{360 - page.rotation}deg",
    "width": f"{field_wdt}pt",
    "height": f"{field_hgt}pt",
    "info": f"[Digitally signed by #{cert_data['cert_name']}\\ Date: {date}]",
    **cert_data,
    **config_params,
    **cli_template_params
  }

  with open(file_in, 'rb') as file:
    w = IncrementalPdfFileWriter(file, strict=False)
    # fields.append_signature_field(
    #     w, sig_field_spec=fields.SigFieldSpec(
    #         'Signature', box=(200, 600, 400, 660)
    #     )
    # )
    signer = signers.SimpleSigner.load_pkcs12(
      pfx_file=cert_path, passphrase=password
    )

    meta = signers.PdfSignatureMetadata(field_name=field_name)
    pdf_signer = signers.PdfSigner(
      meta, signer=signer,
      stamp_style=stamp.StaticStampStyle.from_pdf_file(
        generate_signature_pdf(template_path, template_data),
        border_width=0,
        background_layout= layout.SimpleBoxLayoutRule(
          x_align=layout.AxisAlignment.ALIGN_MID,
          y_align=layout.AxisAlignment.ALIGN_MID,
          margins=layout.Margins.uniform(0),
        )
      )
    )
    if args.output is not None:
      file_out = args.output
    else:
      file_out = inquirer.filepath(
        default=file_in,
        message="Enter path to store output PDF:",
      ).execute()

    # necessary to handle the case of file_in = file_out
    # doc needs to be closed and file_in needs to be closed before writing
    tmp_file = io.BytesIO()
    # print("inplace:", Path(file_out).exists() and os.path.samefile(file_in, file_out))
    pdf_signer.sign_pdf(w, output=tmp_file)

  doc.close()
  with open(file_out, 'wb') as outf:
    outf.write(tmp_file.getvalue())
  tmp_file.close()


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    # gracefully exit on keyboard interrupt
    exit(0)