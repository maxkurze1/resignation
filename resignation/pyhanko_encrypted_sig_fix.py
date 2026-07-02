# Copyright (C) 2025 Max Kurze <max.kurze@barkhauseninstitut.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 or
# later (see LICENSE.md).

"""
Runtime patch for a pyHanko bug when signing *encrypted* PDFs that already
contain a signature dictionary (e.g. a ``/Perms /UR3`` usage-rights signature,
as produced by Adobe Acrobat for many government forms).

Per the PDF spec (ISO 32000, 7.6.2) the ``/Contents`` string of a signature
dictionary is exempt from encryption -- it is stored verbatim. pyHanko's
``DecryptedObjectProxy`` however tries to AES-decrypt every string when it
rewrites objects during signing, including that exempt ``/Contents``. Because
the bytes were never encrypted, the AES-CBC unpadding fails with
``ValueError: Invalid padding bytes`` and signing aborts.

This mirrors the upstream fix (leave the ``/Contents`` of signature
dictionaries untouched) but applies it as a monkey-patch so the script works
with a stock pyHanko install. Importing this module and calling
:func:`apply` installs the patch idempotently.
"""

from pyhanko.pdf_utils import generic
from pyhanko.pdf_utils.generic import (
    DecryptedObjectProxy,
    DictionaryObject,
    StreamObject,
    ArrayObject,
    ByteStringObject,
    TextStringObject,
    Reference,
    proxy_encrypted_obj,
    pdf_string,
)

_PATCH_FLAG = "_resignation_encrypted_sig_patch"


def _looks_like_signature_dict(obj: DictionaryObject) -> bool:
    # /Type is optional, so also check for the characteristic
    # /ByteRange + /Contents combo.
    return obj.get('/Type') in ('/Sig', '/DocTimeStamp') or (
        '/ByteRange' in obj and '/Contents' in obj
    )


@property
def _patched_decrypted(self):
    """Drop-in replacement for ``DecryptedObjectProxy.decrypted`` that leaves
    the (unencrypted) ``/Contents`` of signature dictionaries untouched."""
    if self._decrypted is not None:
        return self._decrypted

    handler = self.handler
    obj = self.raw_object
    container_ref = obj.container_ref
    if not isinstance(container_ref, Reference):
        raise ValueError(
            "Proxyable objects must have a container ref pointing to a "
            f"numbered object, not '{container_ref}'."
        )

    if isinstance(obj, (ByteStringObject, TextStringObject)):
        cf = handler.get_string_filter()
        local_key = cf.derive_object_key(
            container_ref.idnum, container_ref.generation
        )
        decrypted = pdf_string(cf.decrypt(local_key, obj.original_bytes))
    elif isinstance(obj, DictionaryObject):
        skip_contents_decrypt = _looks_like_signature_dict(obj)
        decrypted_entries = {
            # /Contents values in signature dictionaries are exempt from
            # encryption, so leave them untouched.
            dictkey: (
                value
                if (
                    skip_contents_decrypt
                    and dictkey == '/Contents'
                    and isinstance(value, (ByteStringObject, TextStringObject))
                )
                else proxy_encrypted_obj(value, handler)
            )
            for dictkey, value in obj.items()
        }
        if isinstance(obj, StreamObject):
            decrypted = obj._implicit_decrypt_stream_content(
                handler, container_ref, decrypted_entries
            )
        else:
            decrypted = DictionaryObject(decrypted_entries)
    elif isinstance(obj, ArrayObject):
        decrypted = ArrayObject(
            map(lambda v: proxy_encrypted_obj(v, handler), obj)
        )
    else:
        raise TypeError(f'Object of type {type(obj)} is not proxyable.')

    decrypted.container_ref = obj.container_ref
    self._decrypted = decrypted
    return decrypted


def apply():
    """Install the patch (idempotent)."""
    if getattr(DecryptedObjectProxy, _PATCH_FLAG, False):
        return
    DecryptedObjectProxy.decrypted = _patched_decrypted
    setattr(DecryptedObjectProxy, _PATCH_FLAG, True)
