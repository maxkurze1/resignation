#!/usr/bin/env python3

# Copyright (C) 2025 Max Kurze <max.kurze@barkhauseninstitut.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 or
# later (see LICENSE.md).

import fitz  # PyMuPDF
from InquirerPy import prompt
from InquirerPy import inquirer
from InquirerPy.utils import color_print
from InquirerPy.validator import PathValidator
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.base.control import Choice
from .selection_prompt import selection_prompt

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
def get_page_sig_fields(page):
  return list(filter(lambda w: w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE, page.widgets()))
def get_empty_page_sig_fields(page):
  return list(filter(lambda w: not w.is_signed, get_page_sig_fields(page)))

def visual_selection(doc, pg_idx):
  """Open the visual prompt on ``pg_idx`` and return the user's ``Selection``.

  Collects the empty signature fields of *every* page (keeping the global
  field numbering that :func:`page_field_of_idx` resolves) and hands them to
  the prompt in each field's own page points (the ``page.rect`` space).
  Returns ``None`` if the user cancelled.
  """
  counter = 0
  fields = []
  for i, page in enumerate(doc):
    for field in get_empty_page_sig_fields(page):
      # widget.rect is in the page's *unrotated* space; the prompt (and MuPDF's
      # clip / page.rect) work in the rotation-applied display space, so map it
      # across.  rotation_matrix is the identity for un-rotated pages.
      rect = fitz.Rect(field.rect * page.rotation_matrix).normalize()
      fields.append((counter, i, {'x': rect.x0, 'y': rect.y0,
                                  'width': rect.width, 'height': rect.height}))
      counter += 1
  return selection_prompt(doc, fields, page=pg_idx)

def page_field_of_idx(doc, idx):
  # count widgets of prior pages
  for page in doc:
    sig_fields = get_empty_page_sig_fields(page)
    if idx >= len(sig_fields) :
      idx -= len(sig_fields)
      continue
    return page, sig_fields[idx]



from .extract_cert_data import extract_data_from_pk12
from .generate_typst_signature import generate_signature_pdf


from datetime import datetime
import subprocess

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

def resolve_output_name(template, file_in):
  """Resolve an output name template against the input path.

  Supported placeholders (derived from the input file):
    {input} full input path        {dir}  input directory
    {name}  filename without ext    {ext}  extension (incl. leading dot)
  """
  p = Path(file_in)
  substitutions = {
    'input': str(p),
    'dir':   str(p.parent),
    'name':  p.stem,
    'ext':   p.suffix,
  }
  result = template
  for key, value in substitutions.items():
    result = result.replace('{' + key + '}', value)
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


def expand_shell_cmds(key, params):
  value = params[key]

  matches = re.findall(r'\{shell:([^{}]+)\}', value)
  if not matches:
    return value

  for m in matches:
    cmd_out = ""
    try:
      cmd_out = subprocess.check_output(m, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
      print(f"Shell command in parameter failed!", file=sys.stderr)
      print(f"Parameter: '{key}' Command: '{m}' Stderr:", file=sys.stderr)
      print(e.stderr, file=sys.stderr)
      exit(1)
    value = value.replace(f'{{shell:{m}}}', cmd_out)

  return value

def resolve_all(params):
  resolved = {}
  for key in params:
    params[key] = expand_shell_cmds(key, params)
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
from pyhanko.pdf_utils.crypt import StandardSecurityHandler, AuthStatus

from . import pyhanko_encrypted_sig_fix
# Work around a pyHanko bug that aborts signing of encrypted PDFs which
# already contain a signature dict (e.g. Acrobat's /Perms /UR3 usage-rights
# signature) with "ValueError: Invalid padding bytes". See module docstring.
pyhanko_encrypted_sig_fix.apply()

from .fetch import install_typst_stamp, resolve_path
import uuid
from pathlib import Path

def get_cli_version():
  try:
    # only used for local version check
    # python -m resignation.resignation --version
    from setuptools_scm import get_version
    return get_version(root="..", fallback_root="..", relative_to=__file__)
  except Exception:
    # used for nix package
    return os.getenv("SETUPTOOLS_SCM_PRETEND_VERSION", "unknown")

__version__ = get_cli_version()

import argparse
import sys
import io
import tomllib  # built-in since Python 3.11
import keyring
import hashlib
import platform
import re


def file_hash(path):
  with open(path, "rb") as f:
    return hashlib.sha256(f.read()).hexdigest().upper()

def _main():
  parser = argparse.ArgumentParser(prog='resignation', description="digital signature creator")
  parser.add_argument("-i", "--input", help="input PDF file path")
  parser.add_argument("-o", "--output", help="output PDF file path")
  parser.add_argument("--pass", "--password", help="password of certificate (better use --ask)")
  parser.add_argument("--cert", "--certificate", help="path to certificate")
  parser.add_argument("-t", "--template", help="nix-url of stamp-template")
  parser.add_argument("--refresh", action="store_true", help="reload the template")
  parser.add_argument("--offline", action="store_true", help="use cached template")
  parser.add_argument("-c", "--config", help="path to config")
  parser.add_argument("--new-field", help="create new field at \"<page>/<x,y,x2,y2>\"\n or \"<page>/<x,y,+width,+height>\"")
  parser.add_argument("-s", "--sig", help="select which config entry (signature type) to use")
  parser.add_argument("-a", "--ask", action="store_true", help="prompt for password (does not take it from keyring)")
  parser.add_argument("-p", "--param", "--params", action='append', help="template parameter", nargs='*')
  parser.add_argument('--version', action='version', version=f"%(prog)s {__version__}", help="Show version")
  args = parser.parse_args()

  # validate passed params
  if args.refresh and args.offline:
    print("Error: --refresh and --offline are mutually exclusive options!", file=sys.stderr)
    exit(1)

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

  if args.new_field is not None:
    pattern = r"^(\d+)/(\d+),(\d+),(\+?\d+),(\+?\d+)$"
    match = re.match(pattern, args.new_field)
    if not match:
      print("Error: specified --new-field does not match the required format!", file=sys.stderr)
      exit(1)
    page, x, y, w, h = match.groups()
    args.new_field = {
      'page': int(page),
      'x': int(x),
      'y': int(y),
      'width':  int(w) if w.startswith("+") else int(w) - int(x),
      'height': int(h) if h.startswith("+") else int(h) - int(y),
    }

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
  pdf_password = ""
  # check encryption
  if doc.is_encrypted:
    # like adobe - don't ask in case of empty password
    auth_result = doc.authenticate(pdf_password)
    while not auth_result:
      pdf_password = inquirer.secret(
        message=f"Enter pdf password (for {file_in}):",
        transformer=lambda _: "[hidden]",
      ).execute()
      auth_result = doc.authenticate(pdf_password)
      if not auth_result:
        print("wrong password")

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
  field_idx = None
  if args.new_field is not None:
    page_idx = args.new_field['page']
    new_field = args.new_field

  def apply_choice(choice):
    # Map a Selection from the visual prompt onto new_field / field_idx.
    nonlocal new_field, page_idx, field_idx
    if choice is None:
      return False
    if choice.area is not None:
      new_field = choice.area
      page_idx = choice.page
    else:
      field_idx = choice.field
    return True

  def _handle_quit(event):
    # exit the whole application (caught by main() -> exit(0))
    event.app.exit(exception=KeyboardInterrupt)

  # skip loop in case field is explicitly given on CLI
  while True and (args.new_field is None):
    hints = ["[v] visual selection", "[↑/j/↓/k] select", "[q] quit"]

    prompt = inquirer.select(
      message="On which page do you want to sign?",
      choices=page_choices,
      default=None,
      long_instruction="(empty / total)\n" + "   ".join(hints),
      vi_mode=True,
    )

    @prompt.register_kb("v")
    def _handle_visual(event):
      if apply_choice(visual_selection(doc, prompt.result_value)):
        event.app.exit()

    prompt.register_kb("q")(_handle_quit)

    _page_idx = prompt.execute()
    if new_field is not None or field_idx is not None:
      break

    min_idx = 0
    for i in range(_page_idx):
      min_idx += len(get_empty_page_sig_fields(doc[i]))
    max_idx = min_idx + len(get_empty_page_sig_fields(doc[_page_idx])) - 1

    field_idx_opt = None
    if max_idx < min_idx:
      if inquirer.confirm(message="No field on this page, open visual selection?", default=True).execute():
        if apply_choice(visual_selection(doc, _page_idx)):
          break
      continue
    else:
      prompt = inquirer.number(
        message=f"Select which field to sign [{min_idx} - {max_idx}]:",
        min_allowed=min_idx,
        max_allowed=max_idx,
        validate=EmptyInputValidator(),
        long_instruction="[v] visual selection   [esc] back   [q] quit",
        vi_mode=True,
      )

      @prompt.register_kb("v")
      def _handle_visual(event):
        if apply_choice(visual_selection(doc, _page_idx)):
          event.app.exit()

      @prompt.register_kb("escape")
      def _handle_exit(event):
        prompt.application.exit()

      prompt.register_kb("q")(_handle_quit)

      field_idx_opt = prompt.execute()
    # in case escape was pressed execute returns None
    # -> loop back to page selection
    if new_field is not None or field_idx is not None:
      break
    if field_idx_opt is not None:
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
  config_password = None
  config_params = {}
  output_template = None

  if args.config:
    sig_conf = Path(args.config)
  else:
    sig_conf = {
      'Linux': Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser(),
      'Darwin': Path("~/Library/Application Support/").expanduser(),
      'Windows': Path(os.path.expandvars("%APPDATA%")),
    }[platform.system()]/"resignation"/"config.toml"


  sig_conf_dir = sig_conf.resolve().parent

  if sig_conf.expanduser().exists():
    with open(sig_conf.expanduser(), "rb") as f: # must open in binary mode
      data = tomllib.load(f)

    sig_conf_d = None
    if args.sig:
    # TODO check for key error
      sig_conf_d = data[args.sig]
    elif 'default' in data:
      sig_conf_d = data[data['default']]
    else:
      # let user choose template
      keys = [name for name, value in data.items() if isinstance(value, dict)]
      if len(keys) == 0:
        print(f"Warning: Signature config file does not contain entries.", file=sys.stderr)
      else:
        key = inquirer.select(
          message="Which signature type do you wanna use for signing?",
          choices=keys,
          default=None,
          vi_mode=True,
        ).execute()
        sig_conf_d = data[key]

    if sig_conf_d:
      cert_path = resolve_path(sig_conf_dir, sig_conf_d['certificate']) if 'certificate' in sig_conf_d else None
      config_password = sig_conf_d['password'] if 'password' in sig_conf_d else None
      template_path = {"path": sig_conf_d['template'], "relative": sig_conf_dir} if 'template' in sig_conf_d else None
      config_params = sig_conf_d['param'] if 'param' in sig_conf_d else {}
      output_template = sig_conf_d['output'] if 'output' in sig_conf_d else None

  # if value are given on the command line as well, then they have priority
  if args.template:
    # if different template is given on the command line ignore template + params of config
    template_path = {"path": args.template, "relative": '.'}
    config_params = {}
  if not template_path:
    # if config does not contain template then also ignore params of config
    path = inquirer.text(message="Enter signature template url:").execute()
    if not path: # take logo stamp as default if none is provided
      path = "github:maxkurze1/resignation?dir=templates/logo"
    template_path = {"path": path, "relative": '.'}

    config_params = {}

  if args.cert:
    cert_path = Path(args.cert).resolve()
  # if some values are still missing -> prompt user
  if not cert_path:
    cert_path = Path(inquirer.filepath(
      message="Select Certificate file:",
      validate=PathValidator(is_file=True, message="Input is not a file"),
    ).execute()).expanduser().resolve()
  cert_id = file_hash(cert_path)

  if not args.ask:
    try_keyring = True
    if getattr(args, 'pass', None):
      try_keyring = False
      password = getattr(args, 'pass')
      try:
        cert_data = extract_data_from_pk12(cert_path, password.encode())
      except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        exit(1)
    elif config_password is not None:
      try_keyring = False
      password = config_password
      try:
        cert_data = extract_data_from_pk12(cert_path, password.encode())
      except ValueError: # if config pass fails -> try keyring
        try_keyring = True

    if try_keyring:
      password = keyring.get_password("resignation", "sha256:" + cert_id)
      if password is None:
        args.ask = True
      else:
        try:
          cert_data = extract_data_from_pk12(cert_path, password.encode())
        except ValueError: # if keyring fails -> ask
          args.ask = True

  if args.ask: # loop until the user gets it correct
    while True:
      password = inquirer.secret(
        message=f"Enter password (for {cert_path}):",
        transformer=lambda _: "[hidden]",
      ).execute()
      try:
        cert_data = extract_data_from_pk12(cert_path, password.encode())
      except ValueError as e: # if keyring fails -> ask
        print(f"Error: {e}", file=sys.stderr)
        continue
      save_pwd = inquirer.confirm(message="Save password?", default=True).execute()
      if save_pwd:
        keyring.set_password("resignation", "sha256:" + cert_id, password)
      break

  password = password.encode()
  typst_pkg = install_typst_stamp(template_path["path"], template_path["relative"], refresh=args.refresh, offline=args.offline)

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

    if w.security_handler is not None:
      # File is encrypted
      if not isinstance(w.security_handler, StandardSecurityHandler):
        print("Error: Unsupported file encryption", file=sys.stderr)
        exit(1)
      auth_result = w.encrypt(pdf_password)

    if new_field:
      disp = fitz.Rect(
        new_field['x'],
        new_field['y'],
        new_field['x'] + new_field['width'],
        new_field['y'] + new_field['height'],
      )
      box = (disp * ~page.transformation_matrix).normalize()
      new_field_name = str(uuid.uuid4())
      fields.append_signature_field(
        w, sig_field_spec=fields.SigFieldSpec(
          new_field_name, on_page=page_idx,
          box=(box.x0, box.y0, box.x1, box.y1)
        )
      )


    signer = signers.SimpleSigner.load_pkcs12(
      pfx_file=cert_path, passphrase=password
    )
    meta = signers.PdfSignatureMetadata(field_name=new_field_name if new_field else field.field_name)

    # necessary to handle the case of file_in = file_out
    # doc needs to be closed and file_in needs to be closed before writing
    tmp_file = io.BytesIO()
    signers.PdfSigner(
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
    ).sign_pdf(w, output=tmp_file)

  if args.output is not None:
    # replace {name}/{ext}/{dir}/{input} placeholders
    file_out = resolve_output_name(args.output, file_in)
  else:
    # use config provided output name; otherwise fall back to input path
    default_out = resolve_output_name(output_template, file_in) if output_template else file_in
    file_out = inquirer.filepath(
      default=default_out,
      message="Enter path to store output PDF:",
    ).execute()

  doc.close() # free pymupdf buffer (necessary to override file)
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
