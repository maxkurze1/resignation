# Copyright (C) 2025 Max Kurze <max.kurze@barkhauseninstitut.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 or
# later (see LICENSE.md).

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

def get_opt(lst, index, default=None):
  return lst[index].value if -len(lst) <= index < len(lst) else ""

def extract_data_from_pk12(pk12_path, password: str | None = None) -> str | None:
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