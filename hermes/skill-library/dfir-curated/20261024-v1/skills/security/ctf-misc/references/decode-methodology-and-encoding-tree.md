# 解码方法论与编码识别决策树

Day 2（2026-08-26）训练者要求的输出模板与识别判据。原计划并入 SKILL.md，因 SKILL.md 写入守卫问题暂存本参考文件。

## 每题输出模板（训练者要求）
1. **Observation**：字符集、长度、填充、分隔符、重复模式
2. **Candidate**：至少一个候选编码/密码 + 识别理由
3. **Decode Chain**：外层→内层逐步列出操作、参数、每层输出摘要
4. **Reproduction**：实际命令/脚本片段（临时脚本只存 work 目录，不入长期 Memory）
5. **Validation**：最终文本满足 UTF-8/ASCII/flag 结构；**至少用第二种独立方法交叉验证关键转换**
6. **Conclusion** + **Alternatives/Limitations**（歧义、替代解释与排除证据）

禁止：flag 搜索器替代分析（只允许最终遗漏检查）；CyberChef Magic 输出直接当证明；只给 flag 不给解码链；多段/多分支样本未完整解决就组装。

## 编码识别决策树（字符集 → 候选）
- 全 `[0-9a-f]` 且偶数长度 → Hex（`bytes.fromhex`）
- 大写+数字（A–Z, 2–7）+ `=` 填充 → Base32（b32decode 补齐到 8 的倍数）
- `A-Za-z0-9+/=` → Base64；含 `] . /` 等 → 查 Base85 系
- **Base85 变体以字符集区分**：
  - ASCII85（a85）：字符 ord 33–117（含 `] . /`，无 `{}`）；尾部部分组按规范以 `u`(117) 填充取 n-1 字节；python `base64.a85decode(s, adobe=False)` 原生处理
  - b85：`0-9A-Za-z!#$%&()*+-;<=>?@^_`{|}~`（无 `]`）
  - Z85：`0-9a-zA-Z.-:+=^!/*?&<>()[]{}@%$#`（5 字符=4 字节，不支持部分组）
  - RFC1924：`0-9A-Za-z!#$%&()*+-;<=>?@^_`{|}~`（无 `] . /`）
  - 判据法：各字母表逐字符校验 + 各变体解码，仅一种产出文本结构
- `alphabet=` 行 + `ciphertext=` → **换表 Base64**：sorted() 验证 alphabet 是标准表排列 → `str.maketrans(custom, std)` → 标准 b64decode
- `%XX` → URL 百分号（`urllib.parse.unquote`）；`\uXXXX` → Unicode 转义（`bytes(s,'utf-8').decode('unicode_escape')`）；`synt{` 开头 → ROT13（常见内层）
- 经典密码：
  - Vigenère：p=(c-k) mod 26，非字母跳过；多层题两顺序都试，仅一种产出合法 flag 即定序
  - 栅栏：按锯齿路径位置回填重建（先算每行字符数，再按列读）
  - 培根：A/B 五元组 26 字母表，**注意位序**：`AAABA`=00010='c'（不是 00100）
  - 云影：`0` 分隔、各组数字和→字母（96+sum）
  - 仿射：p=a⁻¹(c-b) mod 26，先求模逆（5⁻¹ mod 26 = 21）
- 多进制拼接：bin/base4/octal/hex 分组各自 `int(x, n)` 解码后拼接；拼接处词形完整是验证点（如 `flag{r`+`adix_p`+`aths_m`+`eet}` = `flag{radix_paths_meet}`）
- 多层题（layers=N）：逐层解并记录每层摘要；层顺序/方向用"仅一种顺序产出 flag 结构"判定

## 交叉验证模式
- Base 系：basecrack（`-f 文件` 参数；注意其依赖的解释器版本——缺失模块时换 python3 逐个 import 检查） + Python stdlib 双实现
- Vigenère/仿射：手写实现 + 加密方向复核（明文→密文应等于题目密文）
- 结构证据：file / xxd / exiftool 三方对照；提取物用 file + 结构解析 + SHA-256 独立验证，绝不执行提取内容

## Base64 填充位隐写速查
- 特征：成组 `XX==` 单字节片段；第 2 字符索引低 4 位非零 = 非规范编码（随机概率 ~6.25%）
- 表面解码常给主题提示（如 `PADDING_BITS_REQUIRE_CANONICAL_REENCODING...`），提示不完整/无 flag 结构 → 检查填充位
- 提取：`idx(第2字符) & 0xF` 半字节流 → 两两成字节；验证为可打印 ASCII + flag 结构
- 脚本：`scripts/base64_padding_stego.py`
