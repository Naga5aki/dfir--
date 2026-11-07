# 扩展工作流与历史经验

仅在实际工具接入、格式验证或具体隐写/加密题需要时读取；当前六套 DFIR 的能力和执行边界以主 SKILL.md 与实际 schema 为准。历史路径/性能不是本次健康证据。

# CTF Misc Tooling & Verification

Class-level workflow for CTF Misc work: benign authorized samples only, evidence discipline, and a repeatable tool-onboarding ladder. Originated from SecurityLab Misc bootcamp Day 1 (2026-08-26).

## 适用范围 / Triggers
- 盘点/接入/去重 CTF 工具池（"先盘点、去重、验证，再决定是否接入"）
- 验证工具是否真的可用（`--help`/`--version`/最小样本闭环），禁止"文件存在 = 可用"
- 图片/压缩包/音频/流量/文档隐写题的分析流程
- Windows 上为工具做 wrapper / 激活脚本（中文路径环境下有大量编码陷阱）

## 核心原则
1. **文件存在 ≠ 可用**：每个候选工具必须过 L0→L4 五级，Level 判定全部要有实测输出。
2. **去重靠哈希，不靠大小/名字**：跨目录同名二进制 `find` + `sha256sum` 批量比对；版本差异以 `-h`/`--version` 头部为准（实例：bkcrack 1.8.1 vs 1.7.0 大小不同、hashcat 6.2.6 vs 7.1.2）。
3. **L3 验证用合成最小样本**（已知输入→期望输出，客观可判），不是"看起来像"。训练题样本必须由训练者提供，不得自造自答冒充闭卷。
4. **证据纪律**：原件只读 + 前后 SHA-256；结论按 Observation/Inference/Alternative/Conclusion/Next Validation 分层；字符串/元数据/单一解析器输出不能单独证明行为；flaghunter 类工具只允许分析完成后做遗漏检查。
5. **不下载**：先查工具池与项目内已有副本；下载必须同时满足"无可用副本 + 静态检查+最小功能测试确认不可用 + 报告来源/版本/SHA + 用户授权"。
6. **工具输出先过三关**：任何工具（本机工具集/本机 GUI 工具）的"成功"输出，消费前必须过 格式自检（对照其自身 demo/正确样例）/ 对照实验（同类普通输入产生同构输出 ⇒ 无效）/ 负控制（错误输入被拒）三关；载体文件先做**零成本基扫**（工具族各线各 1 次，含等距/网格类），再进入单路线深挖。

## L0→L4 工具接入阶梯
| 等级 | 判定标准 |
|---|---|
| L0 Found | 确认绝对路径 + 文件大小 |
| L1 Identified | SHA-256 + 类型 + 版本来源（CLI 用 `--version`/`-h` 头；GUI 用 PE VersionInfo）+ 依赖目录 |
| L2 Callable | 只读 `--help`/`--version`/启动检查；GUI 仅确认能打开，不导入证据 |
| L3 Sample-Verified | 合成良性最小样本上得到正确且可复现结果（嵌入→提取闭环 / 已知输入→期望输出） |
| L4 Default-Ready | 路径固定、依赖完整、失败方式已知 → 写入 wrapper + 激活脚本 |

验收门槛参考：核心 CLI ≥12 达 L2、≥8 达 L3、重复下载数 = 0。

## 去重验证法（快速）
```bash
cd <工具池根> && for n in <exe名>; do find . -iname "$n" -type f; done
# 然后对每个副本：
stat -c %s <f>; sha256sum <f>
# 版本差异用工具自身输出，不用文件大小猜：
<exe> -h | head -5   # 或 --version
```
常见重复集中区：EBCTFCodeBox `tools\exe\cli\` 会同时含 bkcrack/dtmf2num/jsteg/snow/npiet/stegdetect/steghide/foremost/mp3stego 等多份副本——优先怀疑。

## Windows 工具链工程（中文路径环境）
- bash wrapper：`exec "<绝对路径>" "$@"`，直接可执行（MSYS 可 exec `D:/...` 风格路径）。
- PowerShell 侧 `.cmd` wrapper **必须 GBK + CRLF**；ps1 含中文路径**必须 UTF-8 BOM**；MSYS→PS 命令行传中文会乱码（用 BOM .ps1 文件规避）。详见 `references/windows-toolchain-pitfalls.md`。
- 干净的多工具目录（如 Wireshark、hashcat 安装目录）直接加进激活脚本 PATH 比逐个 wrapper 更稳；带 DLL 的工具目录（cygwin 等）用 wrapper 避免影子 DLL。
- 若某工具经 cmd.exe 批处理层报"拒绝访问"但 bash 直调正常：不要死磕，用 bash wrapper 或 ps1 直加目录绕过（见 references 文件）。

## 常见坑速查
| 坑 | 事实 | 绕过/方案 |
|---|---|---|
| Python zipfile 加密 | `setpassword` 写入时**不加密**（flag_bits=0x0，仅读取支持 ZipCrypto） | 用 Info-ZIP `zip -P <pw> out.zip file`（Windows 可找 X-Ways 套件自带 zip.exe） |
| hashcat CUDA 报错 | CUDA SDK 缺失 → 自动回退 OpenCL（NVIDIA+AMD 双设备仍可用） | 忽略 HIPRTC/CUDA 报错，直接跑 |
| john `--format=zip` | 显式标签不识别 | 用自动检测 + `--wordlist=<小字典>` |
| foremost 缺 conf | 找不到 foremost.conf 时用内置默认仍可雕刻 | 提取后必须回偏移/签名人工复核 |
| basecrack 依赖 | 正确解释器可能是另一个 python（3.14 有 deps、3.11 缺） | 逐个 `python3 -c "import <mod>"` 检查，别默认用 `python` |
| stegdetect（2004 cygwin） | 现代 Windows 上 ACCESS_VIOLATION 崩溃 | 位平面分析用 StegSolve 替代 |

## 当前 DFIR profile 的能力边界

六套 DFIR profile 不含 CTF Misc Arsenal、CyberChef 或 Sequential Thinking MCP。不要因历史注册记录或下方 references 文档假定它们已接入；不恢复、不执行已删除的 `ctf-arsenal-ensure.py` 或旧 pre_tool_call hook，不改令牌和其他 profile。

- 先按当前 `-p <profile>` 实际 schema 选工具；未注册的工具不能靠猜名调用。当前 Kali SSH `terminal` 可用于已授权样本的本地 CLI，先验证命令、路径、依赖和最小输入。
- CTF/RSA、编码、隐写和压缩包优先现有本地工具或小脚本；限制搜索空间、时长和输出目录。不要为了试工具扫描案件根目录或启动长时爆破。
- PCAP 转 `wire-toutetu`：`dfir-pcap`/`dfir-max` 有 WireMCP。默认已有文件离线分析；实时抓包、凭据提取和联网威胁查询另需明确任务授权。
- 内存转 `memory-forensics-local`：`dfir-mem`/`dfir-max` 有 memforensics。先确认离线/符号前提，不默认全量 triage 或凭据导出。
- EXE/ELF/so 转 `ida-reverse`，APK Java/Smali 转 `android-malware-analysis`：`dfir-re`/`dfir-max` 有对应 MCP。IDA 当前官方服务在 8737，JADX 插件依赖 8650；实际工具名与健康状态以当次发现为准，不沿用旧 GUI/工具数描述。
- MYOS 既有结果转 `myos-results-analysis`；不要把重建索引、解密或重新取证当成普通查询。
- supporting references 中的历史 MCP 路由/恢复步骤仅用于理解旧记录，不构成当前能力或执行授权。保留可复用的编码、样本、格式和脚本细节，调用前按当前环境验证。

### 本机重武器目录 `D:\CTF_Misc_Tools`（Windows 主机历史记录）

下列版本、性能和 EXE 路径属于历史 Windows/MSYS 环境记录，不能当成本次健康检查结论。当前六套 terminal 是 Kali SSH，不能直接执行 `D:/...` Windows EXE；先选 Kali 已有 Linux 工具并验证，或报告缺失。确需 Windows 互操作时另行确认主机执行通道与路径，不自动更改 terminal 后端。

- `压缩包\john-1.9.0-jumbo-1-win64\run\`：**john + rar2john/all2john**。RAR5 本机实测 `--format=rar5` 32 线程 AVX2 ≈ **4161 c/s**；工作流：`rar2john.exe x.rar` → 存 `$rar5$...` 行 → `john.exe --format=rar5 --mask='...' hash.txt`；`--show` 查结果。
- `压缩包\hashcat-6.2.6\`：本机**无 OpenCL 运行时**（`hashcat -I` 报 `./OpenCL No such file`）→ 本机破解优先 john，hashcat 仅备用。
- `随波逐流系列\`：CTF 编码工具 V7.4、二维码识别工具（支持选区/多方法解码）、OCR 工具、224 种编码图、CTF Flags 检查器。
- `图像隐写\`：StegSolve.jar、tweakpng、stegoVeritas、PuzzleSolver、OpenPuff、OurSecret、jsteg、npiet、paperbak、Arnold 猫脸变换、Deformed-Image-Restorer、Acropalypse 等；`实用小工具\`：flaghunter、破空_flag查找、magika、detect-it-easy。
- 上述工具可直接以 bash 调原生 exe（路径用 `D:/...` 正斜杠风格；注意原生程序不认 MSYS `/d/...` 路径）。

### 图像题"看图读字"口令模式（D1no 实训系列观察）

- **模式**：XMP/元数据给出口令骨架（如 `LensMake=D1no_????_2026`），`????` 的填入内容藏在画面手绘/艺术字里；README "保留原始大小写" 往往暗示口令含大写字母。
- **教训**：艺术化手写字形（尤其美术字体变形的拉丁字母）对机器视觉极不友好——形态可被误读为汉字（本次耗时 2 小时+、1300+ 候选未中，字母被误读为「面/鸟/小/口」系）。**止损规则**：字形辨认固定投入上限（如 ~20 次比对），超限即换路线（提示/词表/掩码破解/求助训练者），不在单一图形上无限加码。
- **掩码破解的正确用法**：先穷举最可能的字符类空间与模式变体；**排程铁律**：未知段枚举必须带完整词杆（裸掩码会漏含词杆的真口令），"全小写/全大写/首大写/尾数字"四条短掩码约 15 分钟可全跑完——应整组完成后才进入长程攻击；不要把"全大写短词"（作品名/标签类词汇，如 DUSK）按先验排到最后。若全空间跑完无命中，即证明"不是该字符类"（如本次证明 4 字符非纯小写——而正确答案恰是全大写的 DUSK，是排程覆盖缺口而非算力问题；补跑 `D1no_?u?u?u?u_2026` 仅 2m53s 即命中）。
- **官方路径（WP 验证）**：MISC_03 官方解**不读手写字**——仅 XMP 模板 + 字符类短空间阶梯爆破（`?d`→`?l`→`?u`，各级几分钟）即得口令；手写文字仅是人类读者的辅助提示。**结论：此类题优先短空间爆破，手写辨认不作为主路线。**
- **RAR5 口令自验链（本机已验证）**：`rarfile.RarFile(x).infolist()[0].file_encryption` 直读 (version, flags, lg2, salt?, iv?, check?)，**勿手抄**（漏字节对会使其后所有试口令必然失败）；自验 = `fold8(pw)`（PBKDF2-SHA256(pw, salt, (1<<lg2)+32, 32) 输出的 8 字节 XOR 折叠）比对 check 前 8 字节——lg2=15 时迭代 = **32800**（32768 错）；也可 `rar2john x.rar` → john `--format=rar5` / hashcat `-m 13000 -a 3`（hash 串 `$rar5$16$salt$lg2$iv$8$check8` 两边通用）。
- **停损/优先级**：短掩码组（≈15 分钟）未中时，先检查**排程缺口**（字符类是否全覆盖、词杆是否完整），再考虑语义路线，最后才上长程空间。

### 载体网格提取与加密容器（Case-005 增补）
- **等距/周期性像素网格提取**（图像载体 → 提示/子文件）：参数化模型（起点/步长/块尺寸/行优先）；本 skill `scripts/grid_extract.py` 与 Arsenal 网格类工具互为复核；低对比度产物先二值化+去抖动再逐字符确认；错误步长必须失败（负控制）。细节：`references/equidistant-grid-extraction.md`。
- **加密卷（VeraCrypt/TrueCrypt 类）判定与离线解锁**：无签名恰是符合特征；"成功"输出先过三关（见 `references/output-validity-triple-gate.md`）；离线解锁链（keyfile 池/PBKDF2 表/XTS 官方变体/头部 CRC 自证/主密钥与数据区/文件系统提取）见 `references/veracrypt-offline-unlock.md`，入口 `scripts/vera_unlock.py`。

## 支持文件
- `references/windows-toolchain-pitfalls.md` — 编码/引号/拒绝访问细节与已验证方案、PE VersionInfo 命令
- `references/ctf-misc-arsenal-mcp.md` — CTF Misc Arsenal MCP：题型→工具路由表、调用约定（structured_content/资源产物）、坑与自检
- `references/synthetic-sample-recipes.md` — 可复用的合成最小样本生成配方（PDF/DTMF/pcap/拼接文件/加密 ZIP）
- `references/ooxml-docx-inventory-extraction.md` — OOXML 长文档结构化盘点与保真提取全流程（安全边界/陷阱表/round-trip 验证/阶段门禁恢复）
- `references/equidistant-grid-extraction.md` — 等距/周期性像素网格提取：参数模型、基扫与工具路由、后处理、验证与负控制
- `references/veracrypt-offline-unlock.md` — VeraCrypt/TrueCrypt 类容器判定与离线解锁链：keyfile 池/口令混合、PRF 与迭代表、XTS 官方变体、头部 CRC 自证、数据区与文件系统提取、负控制组
- `references/output-validity-triple-gate.md` — 工具输出有效性"三关"（格式自检/对照实验/负控制）与停止规则
- `scripts/grid_extract.py` — 参数化等距网格提取器（纯标准库；合成样本自测）
- `scripts/vera_unlock.py` — VeraCrypt 类卷离线解锁 + 数据区解密 + FAT 文件提取（pycryptodome；合成卷与原题双环境自测）
- `scripts/crc32_invert.py` — CRC32 ≤4B 明文 GF(2) 线性反解器（含自检）
- `scripts/interleave_reassemble.py` — 无索引交错分片重组器（RAID0 式，含结构自检参数）
