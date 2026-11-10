---
name: ida-reverse
description: Use when EXE/ELF/原生so需IDA逆向、交叉引用或反编译.
---

# IDA Reverse Engineering (Official Hex-Rays MCP)

Use the official IDA MCP, not the old community IDA MCP. It exposes only six tools, so keep calls batched and purposeful.

## 本机边界

静态分析只用 `list_databases`、`open_database`、`execute_python`、`reference`、`save_database`、`close_database`。批量查询放进一次 `execute_python`。不要调用旧社区 IDA 工具名。原样本只读；`save_database` 仅在用户要求保存注释时调用。x64dbg 未接入，不要调用。动态行为写“未取到”。不要写补丁、断点绕过或 dump 后执行。

## Tools

- `list_databases()` — list open IDA sessions / GUI databases.
- `open_database(path, set_current=true)` — attach to the GUI database or spawn a headless idalib worker.
- `execute_python(code, instance_id, timeout)` — run IDAPython; print results to stdout.
- `reference(query)` — ask for IDAPython API docs/snippets when unsure.
- `save_database(instance_id)` — 仅在用户要求保存注释时调用。
- `close_database(instance_id)` — release the session.

## Workflow

1. Call `list_databases()`. If the target is already open, reuse it.
2. Otherwise `open_database("D:/path/sample.exe", set_current=true)`.
3. Use ONE `execute_python` call that batches the read-only queries you need.
4. Only if an API is unfamiliar, call `reference("...")`, then retry.
5. 未获用户要求时不要调用 `save_database`。
6. `close_database(instance_id)` when the analysis is finished.

## IDAPython snippets

Function list (bounded):

```python
import ida_funcs
for i in range(min(ida_funcs.get_func_qty(), 200)):
    f = ida_funcs.getn_func(i)
    print(hex(f.start_ea), ida_funcs.get_func_name(f.start_ea))
```

Decompile the function at the cursor or an address:

```python
import ida_hexrays, ida_funcs, idaapi
ea = 0x401000  # or idaapi.get_screen_ea()
f = ida_funcs.get_func(ea)
print(ida_hexrays.decompile(f.start_ea))
```

Cross-references to a function/address:

```python
import idautils
ea = 0x401000
for x in idautils.XrefsTo(ea):
    print(hex(x.frm), x.type)
```

Strings and imports:

```python
import idautils
for s in idautils.Strings():
    print(hex(s.ea), str(s))
```

```python
import ida_nalt
def cb(ea, name, ordinal):
    print(hex(ea), name or "", ordinal)
for i in range(ida_nalt.get_import_module_qty()):
    print("module:", ida_nalt.get_import_module_name(i))
    ida_nalt.enum_import_names(i, cb)
```

Rename and comment (only when requested):

```python
import ida_name, idaapi
ida_name.set_name(0x401000, "decrypt_packet", ida_name.SN_NOWARN)
idaapi.set_cmt(0x401000, "XOR decrypts the C2 packet", 0)
```

## Rules

- Read-only by default. Rename, patch, or save only when the user asks.
- Batch queries in one `execute_python`; do not make one call per function.
- Limit listings to 200 rows or filter by name/address.
- Use the GUI database when the user says "the IDA window I have open"; otherwise headless is fine.
- If the IDA MCP is unreachable, tell the user to check the local service on `127.0.0.1:8737`; do not start another server.
- For APK/JADX, use `android-malware-analysis`, not this skill.
- 非 APK 二进制的阅读顺序、无符号函数命名和壳/混淆识别见 [references/binary-reading.md](references/binary-reading.md)。APK 里的 `.so` 先走 `android-malware-analysis`。
