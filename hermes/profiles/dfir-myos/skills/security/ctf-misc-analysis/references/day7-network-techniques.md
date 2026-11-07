# Day 7 offline network-capture techniques (PCAP/PCAPNG forensics)

SecurityLab bootcamp day 7: six benign offline captures — damaged PCAP repair, HTTP object
extraction, DNS label tunneling, FTP control/data correlation, ICMP payload reassembly,
TCP out-of-order/retransmission reassembly. All verified against tshark 4.2.0 (fallback path)
+ capinfos 4.7.1 + self-written Python parsers.

## Baseline discipline (per capture)
- `sha256sum -c SHA256SUMS.txt` over all samples FIRST; record each capture's SHA; evidence read-only, everything else in work/.
- `capinfos` for: real format (pcap vs pcapng), encapsulation, interface count, packet count, time range, timestamp precision, SHA.
- Tool health BEFORE use: size + SHA + live `-v` version. A 0-byte binary = BROKEN (empty-file SHA `e3b0c442…`); never claim a version from registry/previous sessions. Stage fallback binaries WITH their DLLs + config/ (tshark.exe alone won't run); copy-then-verify SHA source vs staged.
- Protocol hierarchy `-z io,phs`, IPv4 endpoints `-z endpoints,ipv4`, TCP conversations `-z conv,tcp` LOCATE candidates only. Final evidence per question = display filter + tcp.stream (+frame.number) + raw payload bytes + offsets + SHA.

## Damaged PCAP repair
- Global header layout: magic(4) | version_major(2) version_minor(2) | thiszone(4) | sigfigs(4) | snaplen(4) | network(4). Magic encodes byte order AND timestamp precision: `d4 c3 b2 a1` = LE µs, `a1 b2 c3 d4` = BE ms, `4d 3c b2 a1` = LE ns.
- Zeroed magic (`00 00 00 00`) is the classic single-point damage. If every remaining field parses consistently under little-endian (version 2.4, snaplen 0xffff=65535, network 1=Ethernet) and record headers align, restore `d4 c3 b2 a1` at offset 0-3.
- Cross-check ts_sec/ts_usec against the batch baseline (other samples' earliest packet time) to confirm µs precision.
- Fix ONLY the work copy; record original bytes, fixed bytes, offset, before/after SHA, and tool output before/after (capinfos must go from "isn't a capture file" to full parse).
- After repair, reassemble by APP-LAYER sequence fields, never capture display order.

## Custom protocol header pattern — determine field widths per sample (teacher-corrected)
The same magic family can use DIFFERENT widths per protocol (day 7: SL7R = 4B magic + 1B seq + 1B total, 6B header; SL7I = 4B + 2B seq + 2B total; SL7T = 4B magic + 4B big-endian compressed_length with NO seq/total at all). A previous pass wrongly generalized SL7R/SL7I/SL7T all as "2B seq + 2B total" — the teacher flagged this.
- NEVER generalize one sample's field width to all custom headers. Determine width/endian/header length from: protocol description, length constraints, and MULTIPLE payload samples (e.g. seq bytes forming 0,1,2,… with a constant total byte ⇒ 1B fields; verify with `struct.unpack("!BB", payload[4:6])`).
- Validate: seq set complete `[0..n-1]`, all totals equal, then order by seq. Reassembly output gets its own SHA.
- A length-prefixed stream is NOT a seq/total pair: 4B BE length (`struct.unpack("!I", stream[4:8])`) then exactly that many bytes from offset 8. Verify the compression boundary with `zlib.decompressobj`: eof=True, unused_data empty, unconsumed_tail empty.

## TCP stream reassembly (out-of-order / retransmission)
- Collect server→client segments as (seq, len, payload); sort by seq; stitch with a cursor.
- FULL retransmission = seq+len+bytes already covered → skip silently (report it). PARTIAL overlap = skip dup bytes, and if overlapping bytes differ → report the conflict explicitly.
- tshark analysis flags (`tcp.analysis.out_of_order`, `tcp.analysis.retransmission`) are candidates; verify with raw seq arithmetic yourself.
- `-z follow,tcp,raw,<stream>` output: hex lines with `\t` direction markers (Node0/Node1) — display text, NOT the raw file; cross-check with your own seq stitcher (they must agree byte-for-byte).
- After stitching, verify app header + length field + compression boundary. SIGNATURES: gzip = `1F 8B 08`; `78 01`/`78 5E`/`78 9C`/`78 DA` are ZLIB header combos, NOT gzip magic (calling them "gzip streams" is a teacher-flagged error). Compressed streams can start mid-segment — reassemble fully before parsing. Clean-boundary proof: `zlib.decompressobj`, eof=True, unused_data and unconsumed_tail both empty.

## HTTP object extraction — three layers
1. TCP reassembly (seq stitching; `tcp.segments` frames = segments of a reassembled PDU).
2. HTTP chunked de-chunking: chunk size lines are HEX (`7;part=0`, `B`, `5`, `26`, terminating `0`); optional `;ext` suffix allowed.
3. Content-Encoding decode — choose gzip vs deflate/zlib by the HTTP header AND the actual stream signature: gzip = `1F 8B 08`; zlib = `78 01/5E/9C/DA` (NOT gzip magic).
- `tshark --export-objects http` exports the de-chunked + decompressed body; cross-check with a self-written parser — SHAs must match.
- Key fields: `http.request.uri`, `http.response.code`, `http.transfer_encoding`, `http.content_encoding`.

## DNS label tunneling
- Query direction only (dst port 53). Label structure = seq label + data label + fixed suffix.
- NXDOMAIN (rcode 3) does NOT mean the query labels carry no data.
- Dedupe (same seq + same data), sort by seq, check missing seqs and seq conflicts (same seq, different data = must report).
- Charset `a-z + 2-7` = lowercase base32 (RFC 4648 case-insensitive); pad with `=` to a multiple of 8, decode, hash.

## FTP control/data correlation
- Control stream: USER / PASS / 230 / PASV / RETR. PASV response `(h1,h2,h3,h4,p1,p2)` → data port = p1×256+p2.
- Locate the independent data tcp.stream by that port (server-side ephemeral); extract by TCP seq stitching.
- Credentials go in the report only, never into long-term memory.

## ICMP payload reassembly
- Distinguish request (type 8) / reply (type 0), source address, identifier, sequence.
- Exclude noise packets: different identifier + different source + payload not matching the app structure = ordinary diagnostics.
- Take ONE direction (request side) and sort by app-layer seq — do NOT copy each request AND its reply (that double-counts).

## Windows credential-attack traffic (Pass-the-Hash-style: SMB spray / WinRM / RDP)
From a live two-capture PTH reproduction (SMB spray + WinRM on one target, RDP on another). The constants below are recipes and field names, not sample answers; NTLMv2 material is per-sample evidence — it belongs in the case report, never in long-term memory.
- Shape first: `-z io,phs` — db/nbss/smb/smb2 cluster = Windows file+auth services; http on port 5985 = WinRM; `tls` + `tpkt`/`cotp` + port 3389 = RDP (payload is inside TLS after negotiation).
- Auth inventory: `-Y "ntlmssp" -T fields -e frame.number -e frame.time_epoch -e ip.src -e ip.dst -e tcp.srcport -e tcp.dstport -e ntlmssp.auth.username -e ntlmssp.auth.domain -e ntlmssp.auth.hostname -e ntlmssp.messagetype`, then group by (username, domain, hostname); server-direction frames use high srcports — separate sessions by (srcport,dstport) pairs.
- Per-attempt verdict (SMB1 spray): request/response pairs `smb.cmd==0x73`; count `smb.nt_status` on SERVER-side frames only (client requests also carry 0x0). `0xc0000016` = STATUS_MORE_PROCESSING_REQUIRED (normal mid-handshake), `0xc000006d` = LOGON_FAILURE; success = a response with status 0 after the type3. Operation codes: 0x73 session setup, 0x75 TreeConnect(AndX), 0x74 Logoff, 0x71 TreeDisconnect — read `Path: \\host\share` in `-V` on the TreeConnect frame. Hit→IPC$ TreeConnect→disconnect+logoff within milliseconds = credential validation.
- NTLMv2 material: challenge `ntlmssp.ntlmserverchallenge` (type2 frame), `ntlmssp.auth.ntresponse` (type3) = 16B NTProofStr + blob starting `01 01 00 00`; TargetInfo entries carry UTF-16LE NetBIOS domain / computer / DNS domain — parse them even when the displayed `ntlmssp.auth.domain` is a dummy (e.g. the target IP).
- WinRM: per connection 401 with WWW-Authenticate → type1/2/3 → 200; after 200 the request/response bodies become `multipart/encrypted;protocol="application/HTTP-SPNEGO-session-encrypted"`. Without credential material this is opaque — extract what remains: `OriginalContent: type=application/soap+xml;…;Length=N` header sizes (message-size profiling), session timing, and correlated side effects (a payload download from the victim seconds later). **With credential material (cracked NTLMv2 / PTH) it is NOT a hard stop:** GSS sign/seal keys are derivable and every message decrypts — see "Credential-layer decryption recipes" below.
- Payload identification: PE header machine/sections/TimeDateStamp vs HTTP Last-Modified (a compile time doubles as the served mtime); string clusters classify the tool (e.g. `SamIConnect`/`SamrOpenDomain`/`BCrypt*`/`LsaOpenPolicy` + chrome `logins` SQL = mimikatz; known build: mimikatz 2.2.0 x86 = 1,084,416 B, PE ts 2022-09-19 15:43:55). Export via `--export-objects http,<dir>`; "multipart%2fencrypted" boundary artifacts contain only the envelope.
- RDP: `-V` on the X.224 negotiation — `mstshash=<user>` cookie is plaintext BEFORE TLS; `requestedProtocols` bits (0x01 TLS, 0x02 CredSSP, 0x08 EUA) vs server `selectedProtocol`; a CredSSP request followed by TLS-only retry = NLA-downgrade pattern; server hostname from the TLS cert CN; short RST-terminated attempts vs a long established session with bidirectional application data.
- pcapng block walk (python, read-only): block type@0 (SHB `0A 0D 0D 0A`, IDB 1, SPB 3, NRB 4, ISB 5, EPB 6), total length@4; EPB: iface@8, ts_hi@12, ts_lo@16, caplen@20, origlen@24, data@28. Use it to (a) prove no comment blocks / trailing bytes, (b) map any raw file offset to its FRAME by testing offset ∈ [data_start, data_start+caplen). A grep hit inside a transferred binary is NOT protocol traffic — locate the frame first. Timestamps = 64-bit count in if_tsresol units (default µs). Ready-made walker: `scripts/pcapng_map.py`.
- If a Windows-side read of an exported file fails though the file exists, copy it and read the copy — hash the copied bytes and note the copy (ACL/MOTW layer, not file damage).

### Credential-layer decryption recipes (from a live PTH repro)

Method rules first (both came out of real detours): for any encrypted layer, FIRST find an authoritative implementation or spec constant set (local site-packages, official source) before writing your own code; and before debugging a self-written decryptor, establish a REFERENCE decrypt (a tool's own debug output with intermediate values) and diff layer by layer.

- **WinRM seal/decrypt:** GSS-wrapped body layout = `[4B: verifier length (16)][16B verifier: version(4)+checksum(8)+seq(4)][ciphertext…]`; derive sign/seal keys per the NTLM/SPNEGO spec (hash-magic-string KDF; calibrate against an authoritative lib, e.g. asyauth). Verify EVERY message by its checksum before trusting plaintext (checksum failure = wrong key or layout, not a data quirk). Merge messages split across TCP frames by the length field first. Payload = SOAP/WSMan XML; base64 in output streams decodes to command output.
- **SMB3 (SMB2AESCCM) decrypt:** session key from the NTLM type3 material via MS-NLMP formulas (uppercase(user) + domain as UTF-16LE; HMAC-MD5 chain; RC4 for the exported session key). `EncryptionKey = KDF_CounterMode(SessionKey, b"SMB2AESCCM\0", b"ServerIn \0" / b"ServerOut\0", 128)` — note the KDF byte stream carries the label's trailing NUL plus the KDF's own separator NUL, and the asymmetric context strings: `"ServerIn "` has a trailing SPACE, `"ServerOut"` does NOT. AEAD: tag = the transform header's Signature field, AAD = transform-header bytes `[20:52]`, ciphertext = the whole body, nonce = transform-header bytes `[20:31]`. Different sessions AND directions use different keys (2 sessions = 4 keys); merge writes spanning frames first.
- **TLS 1.0 RSA (cipher 0x002f) decrypt:** the RSA-decrypted premaster carries a 2-byte version prefix (`03 03`); master secret via the TLS 1.0 PRF — split the 48-byte premaster into S1 (first 24 bytes, MD5) and S2 (last 24, SHA1); explicit IV from the record; padding field value = padding bytes − 1 (RFC 2246 — an off-by-one here fails the MAC silently). Get a tool's own decrypted values into a debug file for diffing by passing a protocol value it supports in `tls.keys_list` (e.g. `http`) even when the real subdissector differs.
- **RDP fastpath input (after TLS decrypt):** hand the stream to the right subdissector — set the `tls.keys_list` protocol value to `tpkt` (3389 default-decodes to TPKT; the RDP dissector is a heuristic ON the TPKT table). Fastpath input record: byte0 action `& 0x3 == 0`; byte1 = record length (must equal the segment length); `nevents = (byte0 >> 2) & 0xf` (0 ⇒ an explicit count byte follows); event codes: 0=scancode, 1=mouse, 2=mouseX, 3=sync, 4=unicode; scancode events carry a flags byte + scancode byte. Keycodes → characters via the standard scan-code set; Shift state affects braces/symbols. Verify with TWO independent decode paths (own parser + tshark `rdp.fastpath.*` fields).
- **Negative controls that actually caught things (run one per layer before believing a decryptor):** flipped key / nonce / ciphertext / tag → AEAD rejects; TLS last-byte / middle-byte / wrong-IV / wrong-seq tamper → padding-range or MAC rejection; fastpath length/action mismatches → rejected; wrong pfx password → MAC verify error. Keep every negative control as a one-shot script under the case's analysis dir.

## Pitfalls (tshark field names abort whole command with exit 1)
- Wrong field names kill the entire `-T fields` run: `http.chunk.size`, `tcp.flags.retransmission`, `dns.rcode` are invalid in tshark 4.2. Correct names: `http.transfer_encoding`, `tcp.analysis.retransmission`, `dns.flags.rcode`. Re-run with valid fields rather than assuming empty output.
- More 4.2.0 casualties seen live: `ntlmssp.message_type` (correct: `ntlmssp.messagetype`), `smb.filename`, `rdp.cookie`, `nbns.flags_opcode`, `ntlmssp.ntlmv2res`. When a field name is uncertain, resolve it once with `tshark -G fields | grep -i <term>` instead of guessing a second time.
- Protocol headers can split across TCP segments / chunk boundaries (zlib `78 DA` header split in day 7 T6) — reassemble fully before parsing.
- Single-SYN sessions to many hosts/ports (port-scan shape) are endpoint anomalies, not data streams — exclude from reassembly, note as candidates.
- `follow,tcp,raw` hex includes `\t` direction markers — parse them or write your own stitcher; never write the terminal display straight to a "raw" file.

## Report deliverable completeness (teacher-checked)
- FULL 64-char lowercase SHA-256 for every derivative (evidence ZIP + instruction, each capture, fixed copies, BOTH extraction paths, reassembled streams, decompressed outputs, helper scripts, staged AND source tool binaries). 8-char prefixes are not acceptable; keep sample-level hashes out of long-term memory.
- Per-question "Command / Relevant Output" with REAL executed output: capinfos baseline (damaged files: pre-fix failure AND post-fix success); ONE minimal effective `-Y` display filter (not a bare protocol name); tcp.stream for TCP questions, or explicit "N/A" + the alternative correlation field for non-TCP (udp.srcport / dns.qry.name / icmp.ident); export/follow/field-extraction command + key output; self-written script: command, input, output file, exit status.
- When appending numbered sections (P##) to a shared playbook file, AUDIT existing numbering first — Day 7 wrongly reused Day 6's P29-P31. Renumber by rebuilding the whole affected section with an old→new mapping table; never run a continuous global replace that could overwrite another section. Frequency claims ("most common damage") need statistical backing — say "a candidate damage form" instead.
