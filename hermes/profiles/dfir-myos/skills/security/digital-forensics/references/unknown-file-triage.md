# Unknown-file triage: tooling and conflict diagnostics

This reference holds concrete implementation details for the `digital-forensics` workflow. Re-check package names, versions, and parser source at run time; do not freeze session-specific paths or versions into conclusions.

## Same-shell tool verification on Windows

A Windows path does not identify the shell. Establish the actual environment before installing anything:

```bash
printf 'SHELL=%s\nMSYSTEM=%s\nOSTYPE=%s\nBASH_VERSION=%s\n' \
  "$SHELL" "$MSYSTEM" "$OSTYPE" "$BASH_VERSION"
uname -a
command -v file xxd strings exiftool
file --version
xxd -v
strings --version
exiftool -ver
```

Distinguish Git Bash/MSYS, MSYS2, WSL, PowerShell, and CMD. A tool only counts as provisioned when its bare command runs in the shell that will analyze the samples.

### GNU strings

The requested `strings` may specifically mean GNU Binutils. Confirm that `strings --version` says GNU strings/Binutils. Sysinternals Strings and Python printable-string extraction are useful substitutes, but they are not GNU strings and must be labeled accordingly.

When installation is authorized:

1. Use an OS-trusted package manager or a reputable GNU Binutils distribution.
2. Inspect the package manifest/source and checksum information.
3. Install without elevation when a user-scoped option exists.
4. If a package manager reports command aliases but Git Bash cannot resolve them, locate the package's real `mingw64/bin` (or equivalent) directory, append that directory to the current PATH, run `hash -r`, and repeat `command -v strings` plus `strings --version`.
5. Do not put an entire second MSYS runtime ahead of the current shell's core utilities; append only the required native-tool directory when possible.

A validated route on Windows is a WinGet-listed WinLibs UCRT package whose manifest explicitly includes GNU Binutils. Resolve the current package ID and version dynamically rather than copying an old one.

### Git Bash PATH syntax for Windows directories

Git Bash uses a colon-delimited `PATH`. Do **not** insert a drive-letter form such as `D:/tools/bin` directly: the colon after `D` becomes a path separator, so command lookup silently sees broken entries even though `test -d 'D:/tools/bin'` succeeds. Convert PATH entries to MSYS form (`/d/tools/bin`, `/c/Users/...`) before exporting them. Drive-letter forms remain useful when passing path arguments directly to native Windows executables; this warning applies specifically to colon-delimited POSIX `PATH` values.

### ExifTool Windows portable layout

Use the official ExifTool release page or an OS-trusted package. For the official Windows archive:

1. Obtain the release link and checksum from `exiftool.org`.
2. Verify the downloaded archive before extraction.
3. Rename `exiftool(-k).exe` to `exiftool.exe` for command-line use.
4. Keep the sibling `exiftool_files` directory with the executable.
5. Add that directory to the current shell's PATH and verify `exiftool -ver`.

For Windows-native executables launched from Git Bash, prefer `C:/...` or `D:/...` paths when automatic MSYS path translation is unavailable or disabled.

## Reproducible read-only commands

```bash
file -- "$sample"
xxd -g 1 -l 128 -- "$sample"
strings -a -t x -n 4 -- "$sample"
exiftool -G1 -s -- "$sample"
```

Capture stdout, stderr, and exit status separately when auditability matters. Preserve full raw output outside the evidence directory and quote only type-relevant lines in the report.

### Safe tail offsets for tiny files

Do not blindly use a negative `xxd -s` offset: some builds reject a tail length larger than the file. Compute a non-negative offset:

```bash
size=$(stat -c '%s' -- "$sample")
if [ "$size" -gt 96 ]; then start=$((size-96)); else start=0; fi
xxd -g 1 -s "$start" -l 96 -- "$sample"
```

If a generic batch command fails, preserve the failure, correct only the addressing logic, rerun, and record both the initial error and successful retry.

## Conflict diagnostics

### ExifTool format error versus unsupported format

If ExifTool returns `File format error`:

- retain its non-zero exit and exact message;
- inspect `exiftool -listf` and the installed modules for a handler;
- treat absence of support as a coverage gap, not as evidence against Magic Bytes and independently validated structure;
- do not rename an original merely to coerce a parser.

### Minimal PE and DOS-header warnings

A synthetic or minimal PE may have zero/odd legacy DOS size fields. ExifTool can warn about the DOS-calculated file size while still following `e_lfanew` to a valid `PE\0\0` header. Resolve this by checking:

- `MZ` at offset 0;
- 32-bit `e_lfanew` at `0x3c`;
- `PE\0\0` at the referenced offset;
- COFF/optional header and section bounds.

Report the warning as a structural anomaly, not a type contradiction, when the PE structure independently validates.

### PCAP link-type disagreements

Classic PCAP stores a **32-bit** link type at global-header offset `0x14`. Respect file byte order and decode all four bytes. If a tool reports a different link type:

1. show the four raw bytes;
2. compare the decoded value with an independent classifier/specification;
3. inspect the exact installed parser source for its field offset and width;
4. distinguish the PCAP container conclusion from the disputed link-layer subtype.

A previously observed ExifTool implementation had a correct value-to-name table but read two bytes from offset 22 rather than the 32-bit field at offset 20. Do not assume this remains true in another version—inspect the installed module before attributing the conflict.

## Mechanical integrity check

Write pre- and post-analysis manifests outside evidence, then compare them mechanically:

```bash
sha256sum -- "${samples[@]}" > work/sha256-before.txt
# read-only analysis
sha256sum -- "${samples[@]}" > work/sha256-after.txt
sha256sum -c work/sha256-before.txt
cmp -s work/sha256-before.txt work/sha256-after.txt
```

Also re-enumerate the authorized directory to ensure no reports, extracted members, sidecars, or temporary files were created there.
