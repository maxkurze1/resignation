#!/usr/bin/env python3

import fitz  # PyMuPDF
from InquirerPy import prompt
from InquirerPy import inquirer
from InquirerPy.utils import color_print
from InquirerPy.validator import PathValidator
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.base.control import Choice

def get_page_sig_fields(page):
  return list(filter(lambda w: w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE, page.widgets()))
def get_empty_page_sig_fields(page):
  return list(filter(lambda w: not w.is_signed, get_page_sig_fields(page)))

def show_annotated_page(doc, pg_idx):
  # count widgets of prior pages
  counter = 0
  for i in range(pg_idx):
    counter += len(get_empty_page_sig_fields(doc[i]))

  page = doc[pg_idx]
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

from .selection_prompt import selection_prompt

def create_new_field(doc, pg_idx):
  page = doc[pg_idx]
  page_img = page.get_pixmap(dpi=400).pil_image()
  coords_img = selection_prompt(page_img)
  if not coords_img:
    return None
  xscale, yscale = page.rect.width / page_img.width, page.rect.height / page_img.height

  coords_pg = {
    'x':      coords_img['x']      * xscale,
    'y':      coords_img['y']      * yscale,
    'width':  coords_img['width']  * xscale,
    'height': coords_img['height'] * yscale,
  }
  return coords_pg

def rotate_field(field, width, height, rotation):
  if rotation == 0:
    return {
      'x':      field['x'],
      'y':      height - field['y'] - field['height'],
      'width':  field['width'],
      'height': field['height'],
    }
  elif rotation == 90:
    return {
      'x':      field['y'],
      'y':      field['x'],
      'width':  field['height'],
      'height': field['width'],
    }
  elif rotation == 180:
    return {
      'x':      width - field['x'] - field['width'],
      'y':      field['y'],
      'width':  field['width'],
      'height': field['height'],
    }
  elif rotation == 270:
    return {
      'x':      height - field['y'] - field['height'],
      'y':      width - field['x'] - field['width'],
      'width':  field['height'],
      'height': field['width'],
    }



from .extract_cert_data import extract_data_from_pk12
from .generate_typst_signature import generate_signature_pdf


from datetime import datetime

def get_formatted_date():
  now = datetime.now().astimezone()
  return now.strftime("%d.%m.%Y %H:%M:%S %z")

import re
import sys

def merge_with_precedence(*dicts):
  result = {}
  for d in dicts:
    result.update(d)
  return result

def resolve_param(key, params, seen=None):
  if seen is None:
    seen = set()
  if key in seen:
    print(f"Cycle detected while resolving {key} > {' > '.join(seen)}", file=sys.stderr)
    exit(1)

  seen.add(key)

  if key in params:
    value = params[key]
  else:
    print(f"Unknown parameter: '{key}'", file=sys.stderr)
    exit(1)

  matches = re.findall(r'\{([^{}]+)\}', value)
  if not matches:
    return value

  for m in matches:
    value = value.replace(f'{{{m}}}', resolve_param(m, params, seen.copy()))

  return value

def resolve_all(params):
  resolved = {}
  for key in params:
    resolved[key] = resolve_param(key, params)
  return resolved

import os

def get_env_params(env):
  env_value = os.getenv(env, "")
  env_params = {}
  if env_value:
    for param in env_value.split(":"):
      if "=" in param:
        key, value = param.split("=", 1)
        env_params[key] = value
      else:
        env_params[param] = 'true'
  return env_params


from pyhanko import stamp
from pyhanko.sign import fields, signers
from pyhanko.pdf_utils import layout
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

from .fetch import install_typst_stamp, resolve_path
import uuid
from pathlib import Path

# TODO from importlib.metadata import version
import argparse
import os
import sys
import io
import tomllib  # built-in since Python 3.11

def _main():
  parser = argparse.ArgumentParser(prog='resignation', description="digital signature creator")
  parser.add_argument("-i", "--input", help="input PDF file path")
  parser.add_argument("-o", "--output", help="output PDF file path")
  parser.add_argument("--pass", "--password", help="password of certificate")
  parser.add_argument("--cert", "--certificate", help="path to certificate")
  parser.add_argument("-t", "--template", help="nix-url of stamp-template")
  parser.add_argument("-c", "--config", help="path to config [':'<signature_name>]")
  parser.add_argument("-p", "--param", "--params", action='append', help="template parameter", nargs='*')
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
        cli_template_params[p] = 'true'
        # print(f"Error: invalid input ({p}) - params need to be key value pairs given in the form '<key>=<value>'.", file=sys.stderr)
        # sys.exit(1)

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
  new_field = None
  page_idx = None
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

    @prompt.register_kb("n")
    def _handle_new_field(event):
      nonlocal new_field, page_idx
      new_field = create_new_field(doc, prompt.result_value)
      if new_field:
        page_idx = prompt.result_value
        prompt.application.exit()

    _page_idx = prompt.execute()
    if new_field:
      break

    min_idx = 0
    for i in range(_page_idx):
      min_idx += len(get_empty_page_sig_fields(doc[i]))
    max_idx = min_idx + len(get_empty_page_sig_fields(doc[_page_idx])) - 1

    field_idx_opt = None
    if max_idx < min_idx:
      create_new = inquirer.confirm(message="No field available, create new one?", default=True).execute()
      if create_new:
        new_field = create_new_field(doc, _page_idx)
        page_idx = _page_idx
    else:
      prompt = inquirer.number(
        message=f"Select which field to sign [{min_idx} - {max_idx}] (press 'p' to preview page):",
        min_allowed=min_idx,
        max_allowed=max_idx,
        validate=EmptyInputValidator(),
        vi_mode=True,
      )

      @prompt.register_kb("p")
      def _handle_preview(event):
        show_annotated_page(doc, _page_idx)

      @prompt.register_kb("n")
      def _handle_new_field(event):
        nonlocal new_field, page_idx
        new_field = create_new_field(doc, _page_idx)
        if new_field:
          page_idx = _page_idx
          prompt.application.exit()

      @prompt.register_kb("escape")
      def _handle_exit(event):
        prompt.application.exit()

      field_idx_opt = prompt.execute()
    # in case escape was pressed execute returns None
    # -> loop back to page selection
    if new_field:
      break
    if field_idx_opt:
      field_idx = int(field_idx_opt)
      break

  if not new_field:
    page, field = page_field_of_idx(doc, field_idx)
  else:
    page = doc[page_idx]

  # next: collect certificate path + password + signature template
  cert_path = None
  password = None
  template_path = None
  config_params = {}

  # load all values from config if available
  sig_conf = [Path(os.getenv("XDG_CACHE_HOME", "~/.config")).expanduser() / "resignation" / "config.toml"]
  sig_conf_dir = sig_conf[0].resolve().parent
  if args.config:
    sig_conf = str(args.config).split(':')
    sig_conf_dir = Path(sig_conf[0]).resolve().parent

  if Path(sig_conf[0]).expanduser().exists():
    with open(Path(sig_conf[0]).expanduser(), "rb") as f: # must open in binary mode
      data = tomllib.load(f)

    sig_conf_d = None
    if len(sig_conf) > 1:
      # TODO check for key error
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
      template_path = {"path": sig_conf_d['template'], "relative": sig_conf_dir} if 'template' in sig_conf_d else None
      config_params = sig_conf_d['param'] if 'param' in sig_conf_d else {}

  # if value are given on the command line as well, then they have priority
  if args.template:
    # if different template is given on the command line ignore template + params of config
    template_path = {"path": args.template, "relative": '.'}
    config_params = {}
  if getattr(args, 'pass'):
    password = getattr(args, 'pass').encode()
  if args.cert:
    cert_path = Path(args.cert).resolve()

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
    template_path = {"path": inquirer.text(message="Enter signature template url:").execute(), "relative": '.'}
    config_params = {}

  typst_pkg = install_typst_stamp(template_path["path"], template_path["relative"])
  cert_data = extract_data_from_pk12(cert_path, password)

  # TODO if rotation is set in template it is not clear if the box dimensions should be rotatet too or only the content?
  if new_field:
    field_wdt = new_field['width']
    field_hgt = new_field['height']
  else:
    if page.rotation == 90 or page.rotation == 270:
      field_wdt = field.rect.height
      field_hgt = field.rect.width
    else:
      field_wdt = field.rect.width
      field_hgt = field.rect.height

  template_defaults = {
    "rotation": f"{360 - page.rotation}deg",
    "width": f"{field_wdt}pt",
    "height": f"{field_hgt}pt",
    "date": f"[{get_formatted_date()}]",
  }
  env_params = get_env_params("RESIGNATION_PARAMS")
  merged = merge_with_precedence(template_defaults, cert_data, config_params, env_params, cli_template_params)
  template_data = resolve_all(merged)

  with open(file_in, 'rb') as file:
    w = IncrementalPdfFileWriter(file, strict=False)

    if new_field:
      new_field = rotate_field(new_field, page.rect.width, page.rect.height, page.rotation)
      new_field_name = str(uuid.uuid4())
      fields.append_signature_field(
        w, sig_field_spec=fields.SigFieldSpec(
          new_field_name, on_page=page_idx,
          box=(
            new_field['x'],
            new_field['y'],
            new_field['x'] + new_field['width'],
            new_field['y'] + new_field['height'])
        )
      )

    signer = signers.SimpleSigner.load_pkcs12(
      pfx_file=cert_path, passphrase=password
    )

    meta = signers.PdfSignatureMetadata(field_name=new_field_name if new_field else field.field_name)
    pdf_signer = signers.PdfSigner(
      meta, signer=signer,
      stamp_style=stamp.StaticStampStyle.from_pdf_file(
        generate_signature_pdf(typst_pkg, template_data, template_path["relative"]),
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

def main():
  try:
    _main()
  except KeyboardInterrupt:
    # gracefully exit on keyboard interrupt
    exit(0)

if __name__ == "__main__":
  main()