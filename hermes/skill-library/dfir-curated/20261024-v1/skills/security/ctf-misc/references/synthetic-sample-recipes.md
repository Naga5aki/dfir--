# 合成最小样本生成配方（L3 工具验证用）

原则：已知输入 → 期望输出，客观可判。全部用 Python 标准库，无需下载。训练题样本不在此列（必须由训练者提供）。

## 1. 拼接文件（Binwalk / Foremost 验证）
```python
import zipfile, io
png = open("base.png", "rb").read()
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("hidden.txt", "appended-zip-marker")
open("png_plus_zip.bin", "wb").write(png + buf.getvalue())
# 期望：binwalk 命中 PNG@0 + ZIP@len(png)；foremost -t zip 应提取出 zip
```
`foremost -t zip -i png_plus_zip.bin -o outdir`（找不到 foremost.conf 时用内置默认仍工作）。

## 2. 最小合法 PDF（qpdf --check 验证）
Python 手写对象 + 正确 xref 偏移 + startxref。要点：
- 每个对象记录 `offsets.append(len(pdf))` 再写入；
- xref 表格式 `%010d 00000 n \n`，trailer 的 `/Size = 对象数+1`；
- stream 的 `/Length` 必须与流内容实际字节数一致（本会话曾写 44 实际 41，qpdf 报 WARNING——工具仍可用，但样本不完美）。

## 3. DTMF WAV（dtmf2num 验证）
```python
import wave, math, struct
def dtmf(d):  # 双音合成，8000Hz 16-bit 单声道，每数字 0.18s
    f1, f2 = {"1":(697,1209),"2":(697,1336),"3":(697,1477),"4":(770,1209)}[d]
    return [0.3*(math.sin(2*math.pi*f1*i/8000)+math.sin(2*math.pi*f2*i/8000)) for i in range(int(0.18*8000))]
with wave.open("dtmf1234.wav","w") as fw:
    fw.setnchannels(1); fw.setsampwidth(2); fw.setframerate(8000)
    fw.writeframes(b"".join(struct.pack("<h", int(s*32767)) for s in sum((dtmf(d) for d in "1234"), [])))
# 期望：dtmf2num 输出 "DTMF numbers: 1234"
```

## 4. 手写网络帧 → text2pcap（tshark 验证）
以太网+IPv4+TCP SYN 帧（54 字节），hex 文件带偏移前缀：
```
0000  00 11 22 33 44 55 66 77 88 99 aa bb 08 00 45 00
0010  00 28 00 01 00 00 40 06 7c 66 c0 a8 01 01 c0 a8
0020  01 02 30 39 00 50 00 00 00 01 00 00 00 00 50 02
0030  00 00 ff ff 00 00
```
`text2pcap -q syn.hex test.pcap` → `tshark -r test.pcap` 期望显示 `192.168.1.1 → 192.168.1.2 TCP 54 12345 → 80 [SYN]`。

## 5. 加密 ZIP（bkcrack / zip2john / john 验证）
- **Python zipfile 写入不支持加密**（`setpassword` 仅影响读取；写出 flag_bits=0x0）。这是 Python 已知行为，不是 bug。
- 用 Info-ZIP：`zip.exe -P abc123 pw3.zip flag.txt`（Windows 上 X-Ways 套件自带 `D:\CTF_Misc_Tools\Forensics\X-Ways Forensics\zip.exe`；系统可能另有 7z/bandizip）。
- 验证加密位：`zipfile.ZipFile(...).infolist()[0].flag_bits` 低位为 1（0x9 = 加密+数据描述符）。
- 期望：`zip2john` 输出 `$pkzip2$...`；`john --wordlist=小字典` 自动识别格式破解；`bkcrack -L` 显示 ZipCrypto；已知明文攻击 `bkcrack -C x.zip -c entry -p plain.txt` 恢复内部密钥。

## 6. 其他快件
- 小字典：5~10 行短密码（abc123/pass/123456/password/qwerty），训练场景禁止默认跑 rockyou。
- 位图载体：`magick -size 640x480 xc:gray -attenuate 0.25 +noise Gaussian cover.jpg`——小图（<1KB）会触发 steghide/jsteg "cover too short"，必须用足够大的载体。
