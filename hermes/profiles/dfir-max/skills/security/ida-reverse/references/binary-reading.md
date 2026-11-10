# 二进制阅读顺序、无符号函数与混淆识别

配合 `ida-reverse` 使用。APK 里的 `.so` 只在 `dfir-re` 先走 `android-malware-analysis/references/ctf-quickpass.md` 第 7 节（提取、JNI 名、hex 扫描）；其他 profile 没有这份快答文件，直接按本文件用 IDA。本文件覆盖快答不涉及的部分：非 APK 的二进制、无符号函数、混淆和壳的识别。

所有查询放进一次 `execute_python`。原样本只读，`save_database` 仅在用户要求保存注释时调用。

## 阅读顺序

先定位再反编译，不从函数列表逐个读：

1. 概况：架构、位数、入口。入口落在壳段、导入极少、节区名异常或整体熵高，说明加壳。加壳时结论只覆盖壳，业务逻辑写“未脱壳，未取到”。
2. 锚点先于反编译。优先找导入（`Crypt*`、`BCrypt*`、`EVP_*`、`connect`、`send`、`WinHttp*`、`GetProcAddress`）和字符串（URL、IP、错误提示、算法名）。
3. 用 `idautils.XrefsTo` 找引用锚点的函数，只反编译这些函数。
4. 一个函数读两遍仍说不清就换锚点，不换措辞。同一条路两次没有新增证据就换假设。

## 无符号函数：先查符号表

很多“无符号”函数在动态符号表里有名字。先做这一步：

```python
import idautils
for index, ordinal, ea, name in idautils.Entries():
    print("export", hex(ea), name)
```

有名字就用，不另起一个。`idautils.Names()` 返回 `(ea, name)` 元组，必须解包。

## 命名证据（从强到弱）

| 证据 | 强度 | 例子 |
|---|---|---|
| 动态符号表 / 导出 | 确认 | 直接采用 |
| 调用的导入函数组合 | 强 | 连续 `EVP_CIPHER_CTX_new` + `EVP_DecryptInit_ex` + `EVP_DecryptUpdate` → 解密封装 |
| 引用的字符串 | 强 | 引用 `"invalid signature"` → 签名校验 |
| 立即数常量 | 中 | `0x67452301`（MD5）、`0x6a09e667`（SHA-256）、AES S-box 首字节 `0x63` |
| 只有控制流形状 | 弱 | 不据此命名，标“未确认” |

弱证据不命名。一个函数只给一个名字，名字描述它做什么。

## 混淆：识别后决定是否继续

**控制流平坦化**：单个函数远大于同类函数，一个状态变量驱动 `while(1)` + `switch`，case 之间没有直接关系。本地模型手工还原不划算。记录函数地址和状态变量位置，优先读没被平坦化的函数（字符串解密、校验通常单独存在），结论写“控制流平坦化，业务逻辑未还原”。

**虚假控制流**：大量永远不成立的条件分支。不逐个分析，找引用了字符串或导入函数的基本块，那是真实落点。

**字节码 VM**：入口只做一件事，把一段数据和一张函数指针表交给一个取指-解码-分派循环。opcode 编码每个壳不同，静态猜不可靠。没有运行 trace 就写“VM 壳，编码未还原”，记下解释器循环地址和指针表地址。

## `.so` 的入口以 dynamic 段为准

节区头在脱壳产物里经常是假的。入口看 `DT_INIT`、`DT_INIT_ARRAY` 和 `JNI_OnLoad`，不看 section header。`RegisterNatives` 把 Java native 方法绑定到函数指针，是 Java 到 native 的精确映射，找到这张表就不用猜哪个函数对应哪个 native 方法。

内联系统调用（`svc #0`，调用号在 x8）说明代码绕过 libc 直接调内核，常见于检测逻辑。记下调用号和位置即可，不据此断言“有反调试”。

## 何时停

- 只剩形状判断、没有任何字符串、导入或常量证据：停止命名，写未确认。
- 需要动态 trace 才能区分的分支：写未取到，不补一个“应该会”。
- x64dbg、Frida、radare2、Unicorn 未接入，不要调用。动态行为没有本次运行回执就写未取到。
- IDA MCP 连续失败时，不要写成“没有反汇编器”。改用本机 `C:\Program Files\IDA Professional 9.5\idat.exe -A -S`，或 `android-malware-analysis/scripts/ghidra/export_native_profile.py`。APK 取证快答的提取顺序只在 `dfir-re` 的 `ctf-quickpass.md` 第 7 节。
