#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal .NET IL disassembler for method bodies (debugging stego/CTF tools).

Why this exists: DeepSound's Steganography.dll wraps a divide-by-zero inside
"Input parameter 'length' must be even number". Reading the IL was the only way
to find the root cause (length / decodeQualityMode with an unset field).

Usage:
  python il_disasm.py <hex-il>          # inline hex string
  python il_disasm.py -f <file>         # first line of file is hex IL

Get the hex from PowerShell (32-bit for x86 assemblies):
  $m = $type.GetMethod('Name')
  [BitConverter]::ToString($m.GetMethodBody().GetILAsByteArray()) -replace '-',''
Resolve member tokens with: $m.Module.ResolveMember(0x04000037)

PITFALLS encoded here (each one cost a debugging round):
  * Branch opcodes 0x2B-0x37 (1-byte operand) and 0x38-0x44 (4-byte) must NOT
    live in the single-byte table or the walk desynchronizes immediately.
  * Token-taking opcodes (call 0x28, callvirt 0x6F, ldstr 0x72, newobj 0x73,
    ldfld 0x7B .. stsfld 0x80, ldelema 0x8D, initobj 0xD2, sizeof 0xD8) carry a
    4-byte little-endian token — treat them as 5 bytes, not 1.
  * 0xDE = leave.s (1-byte operand), 0xDD = leave (4-byte).
  * Opcode 0x5B is div, 0x5C is div.un; 0x7A is throw.
"""
import sys

single = {
    0x02:"ldarg.0",0x03:"ldarg.1",0x04:"ldarg.2",0x05:"ldarg.3",
    0x06:"ldloc.0",0x07:"ldloc.1",0x08:"ldloc.2",0x09:"ldloc.3",
    0x0A:"stloc.0",0x0B:"stloc.1",0x0C:"stloc.2",0x0D:"stloc.3",
    0x14:"ldnull",0x15:"ldc.i4.m1",0x16:"ldc.i4.0",0x17:"ldc.i4.1",
    0x18:"ldc.i4.2",0x19:"ldc.i4.3",0x1A:"ldc.i4.4",0x1B:"ldc.i4.5",
    0x1C:"ldc.i4.6",0x1D:"ldc.i4.7",0x1E:"ldc.i4.8",0x25:"dup",0x26:"pop",
    0x27:"jmp",0x2A:"ret",0x45:"switch",
    0x46:"ldind.i1",0x47:"ldind.u1",0x48:"ldind.i2",0x49:"ldind.u2",
    0x4A:"ldind.i4",0x4B:"ldind.u4",0x4C:"ldind.i8",0x4D:"ldind.i",
    0x4E:"ldind.r4",0x4F:"ldind.r8",0x50:"ldind.ref",0x51:"stind.ref",
    0x52:"stind.i1",0x53:"stind.i2",0x54:"stind.i4",0x55:"stind.i8",
    0x56:"stind.r4",0x57:"stind.r8",0x58:"add",0x59:"sub",0x5A:"mul",
    0x5B:"div",0x5C:"div.un",0x5D:"rem",0x5E:"rem.un",0x5F:"and",0x60:"or",
    0x61:"xor",0x62:"shl",0x63:"shr",0x64:"shr.un",0x65:"neg",0x66:"not",
    0x67:"conv.i1",0x68:"conv.i2",0x69:"conv.i4",0x6A:"conv.i8",
    0x6B:"conv.r4",0x6C:"conv.r8",0x6D:"conv.u4",0x6E:"conv.u8",
    0x70:"cpobj",0x71:"ldobj",0x76:"conv.r.un",0x7A:"throw",
    0x81:"stobj",0x8E:"ldelem.i1",0x8F:"ldelem.u1",0x90:"ldelem.i2",
    0x91:"ldelem.u2",0x92:"ldelem.i4",0x93:"ldelem.u4",0x94:"ldelem.i8",
    0x95:"ldelem.i",0x96:"ldelem.r4",0x97:"ldelem.r8",0x98:"ldelem.ref",
    0x9A:"stelem.i1",0x9B:"stelem.i2",0x9C:"stelem.i4",0x9D:"stelem.i8",
    0x9E:"stelem.r4",0x9F:"stelem.r8",0xA0:"stelem.ref",
    0xA3:"conv.ovf.i1",0xA4:"conv.ovf.u1",0xA5:"conv.ovf.i2",
    0xA6:"conv.ovf.u2",0xA7:"conv.ovf.i4",0xA8:"conv.ovf.u4",
    0xA9:"conv.ovf.i8",0xAA:"conv.ovf.u8",0xD0:"volatile.",0xD1:"tail.",
    0xD4:"cpblk",0xD5:"initblk",0xD6:"no.",0xD7:"rethrow",
    0xD9:"refanytype",0xDA:"readonly.",
}
token_ops = {0x20:"ldc.i4",0x28:"call",0x6F:"callvirt",0x72:"ldstr",
    0x73:"newobj",0x74:"castclass",0x75:"isinst",0x79:"unbox",
    0x7B:"ldfld",0x7C:"ldflda",0x7D:"stfld",0x7E:"ldsfld",0x7F:"ldsflda",
    0x80:"stsfld",0x8D:"ldelema",0xA2:"unbox.any",0xD2:"initobj",
    0xD3:"constrained.",0xD8:"sizeof",0xFE:"prefix"}
short1 = {0x0E:"ldarg.s",0x0F:"ldarga.s",0x10:"starg.s",0x11:"ldloc.s",
          0x12:"ldloca.s",0x13:"stloc.s",0x1F:"ldc.i4.s"}
br_s = {0x2B:"br.s",0x2C:"brfalse.s",0x2D:"brtrue.s",0x2E:"beq.s",
        0x2F:"bge.s",0x30:"bgt.s",0x31:"ble.s",0x32:"blt.s",0x33:"bne.un.s",
        0x34:"bge.un.s",0x35:"bgt.un.s",0x36:"ble.un.s",0x37:"blt.un.s"}
br4 = {0x38:"br",0x39:"brfalse",0x3A:"brtrue",0x3B:"beq",0x3C:"bge",
       0x3D:"bgt",0x3E:"ble",0x3F:"blt",0x40:"bne.un",0x41:"bge.un",
       0x42:"bgt.un",0x43:"ble.un",0x44:"blt.un"}


def disasm(il):
    i, n = 0, len(il)
    while i < n:
        op = il[i]
        off = i
        if op in single:
            print(f"{off:03d}  {single[op]}"); i += 1
        elif op in short1:
            print(f"{off:03d}  {short1[op]} {il[i+1]}"); i += 2
        elif op == 0xDE:
            print(f"{off:03d}  leave.s +{il[i+1]}"); i += 2
        elif op == 0xDD:
            print(f"{off:03d}  leave +{int.from_bytes(il[i+1:i+5],'little',signed=True)}"); i += 5
        elif op in br_s:
            print(f"{off:03d}  {br_s[op]} +{il[i+1]}"); i += 2
        elif op in br4:
            print(f"{off:03d}  {br4[op]} +{int.from_bytes(il[i+1:i+5],'little',signed=True)}"); i += 5
        elif op in token_ops:
            print(f"{off:03d}  {token_ops[op]} 0x{int.from_bytes(il[i+1:i+5],'little'):08X}"); i += 5
        elif op == 0x21:
            print(f"{off:03d}  ldc.i8 {int.from_bytes(il[i+1:i+9],'little')}"); i += 9
        elif op == 0x22:
            print(f"{off:03d}  ldc.r4 {il[i+1:i+5].hex()}"); i += 5
        elif op == 0x23:
            print(f"{off:03d}  ldc.r8 {il[i+1:i+9].hex()}"); i += 9
        else:
            print(f"{off:03d}  ?? {op:02X} ({il[i:i+4].hex()})"); i += 1


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "-f":
        il_hex = open(sys.argv[2]).read().strip()
    elif len(sys.argv) >= 2:
        il_hex = sys.argv[1]
    else:
        print(__doc__)
        sys.exit(1)
    disasm(bytes.fromhex(il_hex))
