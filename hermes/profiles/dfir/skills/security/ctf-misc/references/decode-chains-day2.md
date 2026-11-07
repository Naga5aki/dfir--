# Day 2 解码链工作示例（SecurityLab Misc bootcamp，2026-08-26，训练者陌生样本）

12 个文本样本全部解出。每题按训练者要求的模板：Observation → Candidate → Chain → Reproduction → Validation → Conclusion → Alternatives。
关键转换均双方法交叉验证（basecrack v4.0 / python3 3.14 stdlib 独立实现 / 手写实现 + 加密方向复核）。

| # | 识别特征 | 解码链（外层→内层） | 结果 |
|---|---|---|---|
| S01 | 40 个 `[0-9a-f]` 偶数长 | hex → ASCII | `flag{hex_signature_verified}` |
| S02 | 大写+数字(2–7)+`======` | Base32（b32decode 补齐 8 倍数） | `flag{base32_route_checked}` |
| S03 | `A-Za-z0-9+/=` | Base64 | `flag{base64_is_transport_not_proof}` |
| S04 | 含 `] . /` 的 32 字符，全部 ord 33–117 | **ASCII85**（a85decode adobe=False；尾部 2 字符部分组按规范以 `u` 填充取 1 字节） | `flag{ascii85_layer_clear}` |
| S05 | `alphabet=` 64 字符自定义表 + ciphertext | **换表 Base64**：sorted() 验证是标准表排列 → `str.maketrans(custom,std)` → b64decode | `flag{custom_alphabet_mapped}` |
| S06 | 46 行 `XX==` 片段；45/46 非规范填充位 | **Base64 填充位隐写**：表面文本 `PADDING_BITS_REQUIRE_CANONICAL_REENCODING_PADD` 是提示；逐片段 `idx(第2字符)&0xF` → 46 半字节 → 23 字节 | `flag{padding_bits_talk}` |
| S07 | `key=ORBIT layers=3` | b64 → URL 百分号（`%7B`→`{`）→ Vigenère(ORBIT, p=(c-k) mod 26) | `flag{orbit_layers_align}` |
| S08 | `layers=3` 大写 hex | hex → Base32 → **ROT13**（`synt{`=ROT13(`flag{`)） | `flag{hex_base32_rot13_chain}` |
| S09 | `layers=3` Base64 | b64 → URL → Unicode 转义 `\u0066...`（bytes.decode('unicode_escape')） | `flag{unicode_url_base64_chain}` |
| S10 | `assembly=A+B+C+D` | A=二进制(6 字节)→`flag{r`；B=四进制 6 组→`adix_p`；C=八进制 6 组→`aths_m`；D=hex→`eet}`；拼接 | `flag{radix_paths_meet}` |
| S11 | `key=LEMON rails=3 layers=2` | **Rail Fence(3) → Vigenère(LEMON)**；反序产出非 flag 文本即排除 | `flag{rails_then_vigenere}` |
| S12 | PART_A/B/C + AFFINE_A=5,B=8 | 培根（A/B 五元组，`AAABA`=00010='c' 注意位序）→`bacon`；云影（`0` 分隔，8821/821/8881 → 19/11/25 → sky）→`sky`；仿射（a⁻¹=21, p=21(c-8) mod 26）→`AFFINE` | `flag{bacon_sky_AFFINE}`（字面；小写规范 `flag{bacon_sky_affine}`，报备教师） |

## 关键教训
1. **S06 判据**：随机 Base64 片段非规范概率仅 6.25%，45/46 非规范 = 强统计证据；表面提示文字不完整/无 flag 结构 → 检查填充位。
2. **S04 判据**：Base85 变体靠字符集区分——ASCII85 字母表即 ord 33–117；b85/RFC1924 无 `]`；Z85 含 `[]{}`。用各字母表逐字符校验 + 各变体解码，仅一种产出文本结构。
3. **S11 顺序判定**：多层经典密码题两顺序都试，仅一种产出合法 flag 结构即定序。
4. **S12 大小写**：仿射/维吉尼亚类不保留明文大小写，密文大写则解密大写；模板字面组装 vs 小写规范的歧义要写入 Alternatives 报备，不擅自归一。
5. **交叉验证**：basecrack 用 `-f 文件` 参数（`-e` 不接受位置参数）；Vigenère/仿射用"明文→密文应等于题目密文"复核方向。
