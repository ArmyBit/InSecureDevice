from __future__ import annotations

import struct
from pathlib import Path

from capstone import (
    Cs,
    CS_ARCH_ARM,
    CS_ARCH_ARM64,
    CS_ARCH_MIPS,
    CS_ARCH_PPC,
    CS_ARCH_RISCV,
    CS_ARCH_X86,
    CS_MODE_32,
    CS_MODE_64,
    CS_MODE_ARM,
    CS_MODE_THUMB,
)

MAX_INSTRUCTIONS = 150  # limite le prompt (tokens IA)
BYTE_FORMAT = "  .byte {data:02x}"


class DisassemblyError(Exception):
    """Le fichier n'est pas un binaire analysable (PE/ELF) ou non désassemblable."""


class Disassembler:
    """Extraction d'un extrait assembleur d'un binaire PE/ELF (x86, ARM, …).

    Lit les en-têtes, localise le code exécutable (entrée + section .text),
    puis désassemble les premiers MAX_INSTRUCTIONS avec capstone.
    """

    @classmethod
    def disassemble(cls, path: Path, max_instructions: int = MAX_INSTRUCTIONS) -> str:
        with open(path, "rb") as fh:
            data = fh.read()

        if data[:2] == b"MZ":
            code, base, arch, mode = cls._pe_code(data)
        elif data[:4] == b"\x7fELF":
            code, base, arch, mode = cls._elf_code(data)
        else:
            raise DisassemblyError("format non PE/ELF — pas de code machine exploitable")

        if not code:
            raise DisassemblyError("aucune section de code trouvée")

        md = Cs(arch, mode)
        md.detail = False

        lines = []
        for insn in md.disasm(code[: max_instructions * 24], base):
            if len(lines) >= max_instructions:
                break
            lines.append(f"{insn.address & 0xFFFFFFFF:08x}  {insn.mnemonic:<8} {insn.op_str}")
        if not lines:
            raise DisassemblyError("aucune instruction désassemblée")
        return "\n".join(lines)

    # ------------------------------------------------------------- PE ----
    @staticmethod
    def _pe_code(data: bytes) -> tuple[bytes, int, int, int]:
        if len(data) < 0x40:
            raise DisassemblyError("PE tronqué")
        pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_off : pe_off + 4] != b"PE\x00\x00":
            raise DisassemblyError("signature PE manquante")
        machine = struct.unpack_from("<H", data, pe_off + 4)[0]
        nsec = struct.unpack_from("<H", data, pe_off + 6)[0]
        opt_size = struct.unpack_from("<H", data, pe_off + 20)[0]

        arch, mode = Disassembler._machine_arch(machine)
        image_base = 0
        entry_rva = 0
        opt = pe_off + 24
        if opt_size >= 56:
            magic = struct.unpack_from("<H", data, opt)[0]
            if magic == 0x10B:  # PE32
                image_base = struct.unpack_from("<I", data, opt + 28)[0]
                entry_rva = struct.unpack_from("<I", data, opt + 16)[0]
                sec_start = opt + 224
            elif magic == 0x20B:  # PE32+
                image_base = struct.unpack_from("<Q", data, opt + 24)[0]
                entry_rva = struct.unpack_from("<I", data, opt + 16)[0]
                sec_start = opt + 240
            else:
                raise DisassemblyError("OptHead PE inconnu")
        else:
            sec_start = opt

        best = b""
        best_rva = 0
        for i in range(nsec):
            base = sec_start + i * 40
            if base + 40 > len(data):
                break
            vsize, vaddr = struct.unpack_from("<II", data, base + 8)
            raw_size, raw_ptr = struct.unpack_from("<II", data, base + 16)
            if vsize == 0 and raw_size == 0:
                continue
            code = data[raw_ptr : raw_ptr + raw_size]
            cand_rva = vaddr
            if entry_rva and vaddr <= entry_rva < vaddr + vsize:
                off = entry_rva - vaddr
                return code[off:], image_base + entry_rva, arch, mode
            if len(code) > len(best):
                best = code
                best_rva = vaddr
        if best:
            return best, image_base + best_rva, arch, mode
        raise DisassemblyError("aucune section exécutable PE")

    # ------------------------------------------------------------- ELF ----
    @staticmethod
    def _elf_code(data: bytes) -> tuple[bytes, int, int, int]:
        if len(data) < 0x40:
            raise DisassemblyError("ELF tronqué")
        endian = "<" if data[5] == 1 else ">"
        is64 = data[4] == 2

        arch, mode = Disassembler._machine_arch(struct.unpack_from(endian + "H", data, 18)[0])

        if is64:
            e_entry = struct.unpack_from(endian + "Q", data, 24)[0]
            e_phoff, e_shoff, e_ehsize = struct.unpack_from(endian + "QQH", data, 32)
            e_phentsize, e_phnum = struct.unpack_from(endian + "HH", data, 54)
            e_shentsize, e_shnum = struct.unpack_from(endian + "HH", data, 58)
            ph = e_phoff
        else:
            e_entry = struct.unpack_from(endian + "I", data, 24)[0]
            e_phoff, e_shoff, e_ehsize = struct.unpack_from(endian + "III", data, 28)
            e_phentsize, e_phnum = struct.unpack_from(endian + "HH", data, 42)
            e_shentsize, e_shnum = struct.unpack_from(endian + "HH", data, 46)
            ph = e_phoff

        segs = []
        for _i in range(e_phnum):
            if ph + e_phentsize > len(data):
                break
            if is64:
                p_type, _p_flags, p_offset, p_vaddr = struct.unpack_from(endian + "IIQQ", data, ph + 4 + 0)
                p_filesz = struct.unpack_from(endian + "Q", data, ph + 4 + 24)[0]
            else:
                p_type, p_offset, p_vaddr, _p_paddr, p_filesz = struct.unpack_from(endian + "IIIII", data, ph)
            if p_type == 1:  # PT_LOAD
                segs.append((p_vaddr, p_offset, p_filesz))
            ph += e_phentsize

        segs.sort(key=lambda s: s[0])
        if not segs:
            raise DisassemblyError("aucun segment ELF exécutable")

        for vaddr, off, size in segs:
            code = data[off : off + size]
            if e_entry and vaddr <= e_entry < vaddr + size:
                return code[abs(e_entry - vaddr) :], e_entry, arch, mode
        vaddr, off, size = segs[0]
        return data[off : off + size], vaddr, arch, mode

    # ------------------------------------------------------------- arch ----
    @staticmethod
    def _machine_arch(machine: int) -> tuple[int, int]:
        table = {
            0x014C: (CS_ARCH_X86, CS_MODE_32),  # I386
            0x8664: (CS_ARCH_X86, CS_MODE_64),  # AMD64
            0x01C4: (CS_ARCH_ARM, CS_MODE_ARM),  # ARM
            0xAA64: (CS_ARCH_ARM64, CS_MODE_ARM),  # ARM64
            0x0166: (CS_ARCH_MIPS, CS_MODE_32),  # MIPS
            0x01F0: (CS_ARCH_PPC, CS_MODE_32),  # PPC
        }
        if machine in table:
            return table[machine]
        # ELF EM_* (différent de PE) : géré via détection heuristique
        if machine in (40, 62):  # EM_ARM / EM_X86_64
            return (CS_ARCH_X86, CS_MODE_64) if machine == 62 else (CS_ARCH_ARM, CS_MODE_ARM)
        if machine == 3:
            return CS_ARCH_X86, CS_MODE_32  # EM_386
        if machine == 183:
            return CS_ARCH_ARM64, CS_MODE_ARM  # EM_AARCH64
        if machine in (8, 243):  # EM_MIPS
            return CS_ARCH_MIPS, CS_MODE_32
        if machine == 21:
            return CS_ARCH_PPC, CS_MODE_32  # EM_PPC
        if machine == 0xF3:
            return CS_ARCH_RISCV, CS_MODE_32
        raise DisassemblyError(f"architecture non supportée (machine={machine:#x})")


def extract_assembly(path: Path, max_instructions: int = MAX_INSTRUCTIONS) -> tuple[str, str]:
    """Retourne (extrait assembleur, message d'erreur éventuel)."""
    try:
        return Disassembler.disassemble(path, max_instructions), ""
    except (DisassemblyError, OSError, struct.error) as exc:
        return "", str(exc)