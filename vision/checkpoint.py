"""Bounded static inspection. Never unpickles or imports checkpoint-supplied code.

This produces evidence, not a security verdict. Dynamic STACK_GLOBAL references,
REDUCE behavior, and runtime effects cannot be cleared by this inspection.
"""

import pickletools
import zipfile
from pathlib import Path, PurePosixPath

from vision.provenance import sha256_file

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_PICKLE_BYTES = 4 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_MEMBERS = 4096


def inspect_checkpoint(path: Path) -> dict:
    size = path.stat().st_size
    if size > MAX_ARCHIVE_BYTES:
        raise ValueError("checkpoint exceeds the 64 MiB inspection limit")
    if not zipfile.is_zipfile(path):
        raise ValueError("expected a modern PyTorch ZIP checkpoint")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > MAX_MEMBERS:
            raise ValueError("too many archive members")
        if len({item.filename for item in members}) != len(members):
            raise ValueError("duplicate archive members")
        if sum(item.file_size for item in members) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("uncompressed archive exceeds inspection limit")
        for member in members:
            # zipfile normalizes backslashes on Windows. Inspect the raw name too
            # so the same archive receives the same verdict on Windows and Linux.
            original = member.orig_filename
            name = PurePosixPath(original)
            if name.is_absolute() or ".." in name.parts or "\\" in original:
                raise ValueError("unsafe archive member name")
            if member.flag_bits & 1:
                raise ValueError("encrypted archive members are unsupported")
        pickles = [item for item in members if PurePosixPath(item.filename).name == "data.pkl"]
        if len(pickles) != 1:
            raise ValueError("expected exactly one data.pkl member")
        entry = pickles[0]
        if entry.file_size > MAX_PICKLE_BYTES:
            raise ValueError("pickle metadata exceeds inspection limit")
        globals_found: set[str] = set()
        dynamic_globals = 0
        opcodes = 0
        # genops parses opcode bytes; it does not execute pickle instructions.
        for opcode, argument, _ in pickletools.genops(archive.read(entry)):
            opcodes += 1
            if opcode.name == "GLOBAL":
                globals_found.add(argument.replace(" ", ".", 1))
            elif opcode.name == "STACK_GLOBAL":
                dynamic_globals += 1
    return {
        "schema_version": 1,
        "inspection": "static_only_not_security_clearance",
        "filename": path.name,
        "sha256": sha256_file(path),
        "size_bytes": size,
        "archive_members": len(members),
        "pickle_bytes": entry.file_size,
        "pickle_opcodes": opcodes,
        "globals": sorted(globals_found),
        "dynamic_globals": dynamic_globals,
        "load_performed": False,
    }
