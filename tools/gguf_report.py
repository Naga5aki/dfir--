#!/usr/bin/env python3
"""Read-only GGUF inventory for the local Qwen3.8 model.

Usage:
  python -I gguf_report.py <model.gguf> [out.json]

Parses the GGUF header, metadata scalars, and every tensor descriptor.
No inference, no model loading, no network.
"""
import json
import os
import struct
import sys
from collections import Counter, defaultdict

# ggml type id -> (name, block_elems, bytes_per_block)
# Only types present in this model are strictly needed, but keep the common set.
GGML_TYPES = {
    0:  ("F32",      1,   4),
    1:  ("F16",      1,   2),
    2:  ("Q4_0",     32,  18),
    3:  ("Q4_1",     32,  20),
    6:  ("Q5_0",     32,  22),
    7:  ("Q5_1",     32,  24),
    8:  ("Q8_0",     32,  34),
    9:  ("Q8_1",     32,  36),
    10: ("Q2_K",     256, 84),
    11: ("Q3_K",     256, 110),
    12: ("Q4_K",     256, 144),
    13: ("Q5_K",     256, 176),
    14: ("Q6_K",     256, 210),
    15: ("Q8_K",     256, 292),
    16: ("IQ2_XXS",  256, 66),
    17: ("IQ2_XS",   256, 74),
    18: ("IQ3_XXS",  256, 98),
    19: ("IQ1_S",    256, 50),
    20: ("IQ4_NL",   32,  18),
    21: ("IQ3_S",    256, 110),
    22: ("IQ2_S",    256, 82),
    23: ("IQ4_XS",   256, 136),
    24: ("I8",       1,   1),
    25: ("I16",      1,   2),
    26: ("I32",      1,   4),
    27: ("I64",      1,   8),
    28: ("F64",      1,   8),
    29: ("IQ1_M",    256, 56),
    30: ("BF16",     1,   2),
    34: ("TQ1_0",    256, 54),
    35: ("TQ2_0",    256, 66),
}

# GGUF metadata value type ids
U8, I8, U16, I16, U32, I32, F32, BOOL, STR, ARR, U64, I64, F64 = range(13)
FIXED = {U8: (1, "<B"), I8: (1, "<b"), U16: (2, "<H"), I16: (2, "<h"),
         U32: (4, "<I"), I32: (4, "<i"), F32: (4, "<f"), BOOL: (1, "<?"),
         U64: (8, "<Q"), I64: (8, "<q"), F64: (8, "<d")}


def read_exact(f, n):
    b = f.read(n)
    if len(b) != n:
        raise EOFError(f"wanted {n} bytes, got {len(b)}")
    return b


def read_u32(f):
    return struct.unpack("<I", read_exact(f, 4))[0]


def read_u64(f):
    return struct.unpack("<Q", read_exact(f, 8))[0]


def read_string(f):
    n = read_u64(f)
    return read_exact(f, n).decode("utf-8", errors="replace")


def skip_value(f, vtype):
    if vtype in FIXED:
        size, _ = FIXED[vtype]
        f.seek(size, os.SEEK_CUR)
    elif vtype == STR:
        n = read_u64(f)
        f.seek(n, os.SEEK_CUR)
    elif vtype == ARR:
        etype = read_u32(f)
        n = read_u64(f)
        if etype in FIXED:
            size, _ = FIXED[etype]
            f.seek(size * n, os.SEEK_CUR)
        elif etype == STR:
            for _ in range(n):
                ln = read_u64(f)
                f.seek(ln, os.SEEK_CUR)
        else:
            raise ValueError(f"unsupported array element type {etype}")
    else:
        raise ValueError(f"unsupported metadata type {vtype}")


def read_value(f, vtype):
    if vtype in FIXED:
        size, fmt = FIXED[vtype]
        return struct.unpack(fmt, read_exact(f, size))[0]
    if vtype == STR:
        return read_string(f)
    if vtype == ARR:
        etype = read_u32(f)
        n = read_u64(f)
        # Keep small numeric arrays, skip huge tokenizer string arrays.
        if etype in FIXED and n <= 65536:
            size, fmt = FIXED[etype]
            return list(struct.unpack("<" + fmt[1] * n, read_exact(f, size * n)))
        skip_value(f, ARR)  # not reached: ARR header already consumed
        return f"<array type={etype} n={n}>"
    raise ValueError(f"unsupported metadata type {vtype}")


def nbytes(ne, ttype):
    n = 1
    for d in ne:
        n *= d
    if ttype not in GGML_TYPES:
        return None
    _, block, nbytes_block = GGML_TYPES[ttype]
    if block == 1:
        return n * nbytes_block
    if n % block != 0:
        raise ValueError(f"element count {n} not divisible by block {block} for type {ttype}")
    return (n // block) * nbytes_block


def main():
    path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    with open(path, "rb") as f:
        magic = read_exact(f, 4)
        if magic != b"GGUF":
            raise SystemExit("not a GGUF file")
        version = read_u32(f)
        n_tensors = read_u64(f)
        n_kv = read_u64(f)

        meta = {}
        for _ in range(n_kv):
            key = read_string(f)
            vtype = read_u32(f)
            if vtype == ARR:
                etype = read_u32(f)
                n = read_u64(f)
                # Always skip array payloads here; large tokenizer arrays dominate.
                if etype in FIXED:
                    size, _ = FIXED[etype]
                    f.seek(size * n, os.SEEK_CUR)
                elif etype == STR:
                    for _ in range(n):
                        ln = read_u64(f)
                        f.seek(ln, os.SEEK_CUR)
                else:
                    raise ValueError(f"unsupported array element type {etype}")
                meta[key] = f"<array type={etype} n={n}>"
            else:
                meta[key] = read_value(f, vtype)

        tensors = []
        for _ in range(n_tensors):
            name = read_string(f)
            nd = read_u32(f)
            ne = [read_u64(f) for _ in range(nd)]
            ttype = read_u32(f)
            off = read_u64(f)
            tensors.append({"name": name, "ne": ne, "type": ttype, "offset": off,
                            "nbytes": nbytes(ne, ttype)})

    type_counts = Counter(t["type"] for t in tensors)
    type_bytes = defaultdict(int)
    for t in tensors:
        if t["nbytes"] is not None:
            type_bytes[t["type"]] += t["nbytes"]

    blocks = defaultdict(lambda: {"bytes": 0, "tensors": 0, "kinds": set()})
    for t in tensors:
        name = t["name"]
        if name.startswith("blk."):
            bid = int(name.split(".")[1])
            b = blocks[bid]
            b["bytes"] += t["nbytes"] or 0
            b["tensors"] += 1
            if ".ssm_" in name:
                b["kinds"].add("linear_ssm")
            if ".attn_q." in name or ".attn_k." in name or ".attn_v." in name:
                b["kinds"].add("full_attn")
            if ".nextn." in name:
                b["kinds"].add("mtp_nextn")

    def block_list(pred):
        return [i for i in sorted(blocks) if pred(i)]

    main_blocks = [i for i in sorted(blocks) if i < 64]
    mtp_blocks = [i for i in sorted(blocks) if i >= 64]

    def block_bytes(ids):
        return sum(blocks[i]["bytes"] for i in ids)

    token_embd = next((t["nbytes"] for t in tensors if t["name"] == "token_embd.weight"), 0)
    output = next((t["nbytes"] for t in tensors if t["name"] == "output.weight"), 0)
    output_norm = next((t["nbytes"] for t in tensors if t["name"] == "output_norm.weight"), 0)

    # Placement derived from llama.cpp c0fd78626:
    # i_gpu_start = max(n_layer_all + 1 - n_gpu_layers, 0)
    # n_layer_all = 65 (64 trunk + 1 MTP block); input embeddings stay on CPU.
    def placement(n_gpu_layers, load_mtp):
        n_layer_all = 65
        i_gpu_start = max(n_layer_all + 1 - n_gpu_layers, 0)
        gpu_blocks = [i for i in range(64) if i >= i_gpu_start]
        cpu_blocks = [i for i in range(64) if i < i_gpu_start]
        gpu = block_bytes(gpu_blocks) + output + output_norm
        cpu = block_bytes(cpu_blocks) + token_embd
        if load_mtp:
            # block 64 follows dev_layer[64]; GPU when 64 >= i_gpu_start
            if 64 >= i_gpu_start:
                gpu += block_bytes(mtp_blocks)
            else:
                cpu += block_bytes(mtp_blocks)
        return {"n_gpu_layers": n_gpu_layers, "i_gpu_start": i_gpu_start,
                "gpu_blocks": gpu_blocks, "cpu_blocks": cpu_blocks,
                "gpu_weight_bytes": gpu, "cpu_weight_bytes": cpu,
                "mtp_loaded": bool(load_mtp)}

    block_summary = {}
    for i in sorted(blocks):
        block_summary[str(i)] = {
            "bytes": blocks[i]["bytes"],
            "mib": round(blocks[i]["bytes"] / 1024 / 1024, 2),
            "tensors": blocks[i]["tensors"],
            "kinds": sorted(blocks[i]["kinds"]),
        }

    report = {
        "file": os.path.abspath(path),
        "file_bytes": os.path.getsize(path),
        "gguf_version": version,
        "tensor_count": n_tensors,
        "metadata_subset": {k: v for k, v in meta.items() if not isinstance(v, str) or not v.startswith("<array")},
        "metadata_array_keys": sorted([k for k, v in meta.items() if isinstance(v, str) and v.startswith("<array")]),
        "type_counts": {str(k): v for k, v in sorted(type_counts.items())},
        "type_names": {str(k): GGML_TYPES.get(k, ("?",))[0] for k in sorted(type_counts)},
        "type_bytes": {str(k): v for k, v in sorted(type_bytes.items())},
        "total_tensor_bytes": sum((t["nbytes"] or 0) for t in tensors),
        "token_embd_bytes": token_embd,
        "output_bytes": output,
        "output_norm_bytes": output_norm,
        "mtp_bytes": block_bytes(mtp_blocks),
        "main_block_bytes": block_bytes(main_blocks),
        "block_summary": block_summary,
        "full_attn_blocks": block_list(lambda i: "full_attn" in blocks[i]["kinds"] and i < 64),
        "linear_ssm_blocks": block_list(lambda i: "linear_ssm" in blocks[i]["kinds"] and i < 64),
        "mtp_blocks": mtp_blocks,
        "placement_ngl64_no_mtp": placement(64, False),
        "placement_ngl_all_no_mtp": placement(66, False),
        "placement_ngl64_with_mtp": placement(64, True),
        "placement_ngl_all_with_mtp": placement(66, True),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as g:
            g.write(text + "\n")
        print(f"wrote {out_path}")
        print(f"tensors={n_tensors} types={report['type_names']} blocks={len(blocks)} "
              f"full_attn={len(report['full_attn_blocks'])} linear={len(report['linear_ssm_blocks'])} "
              f"mtp_bytes={report['mtp_bytes']}")
    else:
        print(text)


if __name__ == "__main__":
    main()
