"""Report-only comparison of six independent DFIR configs; never imports Hermes.

Run with an existing Python containing ruamel.yaml and -B. No environment expansion,
credential-file access, profile enumeration, repair, or runtime commands are performed.
The opt-in template generator writes one NEW JSON artifact inside this script's staged
directory. It refuses incomplete/noncommon snapshots and credential literals.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlsplit


PROFILES = ("dfir", "dfir-myos", "dfir-re", "dfir-mem", "dfir-pcap", "dfir-max")
MANAGED_PATHS = (
    "model", "terminal", "skills.auto_load", "hooks", "platform_toolsets",
    "auxiliary.title_generation.model_upgrade_enabled",
)
STAGING_ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILES_ROOT = Path("D:/ForensicsAgent/hermes/profiles")
MAX_INPUT_BYTES = 1024 * 1024
_MISSING = object()
_ENV_REF = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}\Z")
_SECRET_NAMES = frozenset({
    "key", "api_key", "apikey", "api_token", "token", "password", "passwd",
    "passphrase", "secret", "client_secret", "access_key", "access_key_id",
    "secret_access_key", "access_token", "refresh_token", "credential", "credentials",
    "authorization", "proxy_authorization", "cookie", "set_cookie",
})
_INLINE_ASSIGNMENT = re.compile(
    r"(?i)(?:\b|--)(?:api[-_]?key|api[-_]?token|access[-_]?token|password|passwd|passphrase|"
    r"client[-_]?secret|token|secret)\s*(?:[:=]\s*|\s+)[\"']?([^\s\"';]+)"
)
_KNOWN_SECRET = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|"
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"AKIA[A-Z0-9]{16}|AIza[0-9A-Za-z_-]{30,}|hf_[A-Za-z0-9]{20,})\b"
)


def _finding(profile: str, path: str, issue: str) -> dict:
    # Only caller-controlled FIXED labels belong here. Never echo input keys or values.
    return {"profile": profile, "path": path, "issue": issue}


def _plain_json(value, *, depth=0, seen=None):
    """Reject YAML-specific objects, recursion and non-string mapping keys."""
    if depth > 30:
        raise ValueError("unsupported_structure")
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("unsupported_number")
        return value
    if type(value) not in (dict, list):
        raise ValueError("unsupported_type")
    seen = set() if seen is None else seen
    if id(value) in seen:
        raise ValueError("recursive_structure")
    seen = seen | {id(value)}
    if isinstance(value, list):
        return [_plain_json(v, depth=depth + 1, seen=seen) for v in value]
    if any(type(k) is not str for k in value):
        raise ValueError("unsupported_key")
    return {k: _plain_json(v, depth=depth + 1, seen=seen) for k, v in value.items()}


def _secret_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return normalized in _SECRET_NAMES or normalized.endswith(("_password", "_secret", "_api_key", "_token"))


def _reference(value) -> bool:
    return isinstance(value, str) and bool(_ENV_REF.fullmatch(value))


def _credential_value_safe(value) -> bool:
    if value is None or value == "":
        return True
    if _reference(value):
        return True
    # Authorization headers can retain a literal scheme plus an unexpanded reference.
    return isinstance(value, str) and value.startswith("Bearer ") and _reference(value[7:])


def _has_secret_literal(value) -> bool:
    """Conservative rejection, not a proof that arbitrary prose contains no secrets."""
    if isinstance(value, dict):
        for key, child in value.items():
            if _secret_key(key) and not _credential_value_safe(child):
                return True
            # ssh_key is an identity-file pathname, not private key material.
            if key.casefold().replace("-", "_") == "ssh_key" and child not in (None, ""):
                if not isinstance(child, str) or not (
                    _reference(child) or child.startswith(("/", "~/")) or re.match(r"^[A-Za-z]:[/\\]", child)
                ):
                    return True
            if _has_secret_literal(child):
                return True
        return False
    if isinstance(value, list):
        return any(_has_secret_literal(item) for item in value)
    if not isinstance(value, str):
        return False
    if _KNOWN_SECRET.search(value):
        return True
    for match in _INLINE_ASSIGNMENT.finditer(value):
        if not _reference(match.group(1)):
            return True
    for candidate in re.findall(r"https?://[^\s\"'<>]+", value):
        try:
            parsed = urlsplit(candidate)
            if "@" in parsed.netloc:
                return True
            if any(_secret_key(k) and not _reference(v) for k, v in parse_qsl(parsed.query)):
                return True
        except ValueError:
            return True
    return False


def _read_text(path: Path) -> str:
    with path.open("rb") as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input_too_large")
    return raw.decode("utf-8-sig")


def _config_path(root: Path, profile: str) -> Path:
    """Refuse a fixed profile/config link escaping its named child of the chosen root."""
    directory = root / profile
    resolved = directory.resolve()
    if resolved != root / profile:
        raise ValueError("scope_escape")
    path = directory / "config.yaml"
    if path.resolve() != resolved / "config.yaml":
        raise ValueError("scope_escape")
    return path


def _get(config: dict, dotted: str):
    value = config
    for name in dotted.split("."):
        if not isinstance(value, dict) or name not in value:
            return _MISSING
        value = value[name]
    return value


def load_profiles(root: Path) -> tuple[dict, list[dict]]:
    from ruamel.yaml import YAML
    snapshots, findings = {}, []
    root = root.resolve()
    for profile in PROFILES:
        try:
            path = _config_path(root, profile)
        except (OSError, ValueError, RuntimeError):
            findings.append(_finding(profile, "config.yaml", "scope_escape"))
            continue
        try:
            source = _read_text(path)
        except (OSError, UnicodeError, ValueError):
            findings.append(_finding(profile, "config.yaml", "unreadable_config"))
            continue
        try:
            parser = YAML(typ="safe", pure=True)
            parser.allow_duplicate_keys = False
            config = _plain_json(parser.load(source))
            if not isinstance(config, dict):
                raise ValueError("root_not_mapping")
        except Exception:
            # Parser exceptions include source excerpts; they must never reach the report.
            findings.append(_finding(profile, "config.yaml", "invalid_yaml"))
            continue
        if _has_secret_literal(config):
            findings.append(_finding(profile, "config.yaml", "secret_literal"))
            continue
        values = {}
        for field in MANAGED_PATHS:
            value = _get(config, field)
            if value is _MISSING:
                findings.append(_finding(profile, field, "missing"))
            else:
                values[field] = value
        snapshots[profile] = values
    return snapshots, findings


def _json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def load_template(path: Path) -> tuple[dict | None, list[dict]]:
    try:
        path = path.resolve()
        if not path.is_relative_to(STAGING_ROOT):
            return None, [_finding("template", "template", "outside_staging")]
    except (OSError, ValueError, RuntimeError):
        return None, [_finding("template", "template", "outside_staging")]
    try:
        if path.suffix.casefold() != ".json":
            raise ValueError("json_required")
        template = json.loads(_read_text(path), object_pairs_hook=_json_pairs)
        template = _plain_json(template)
        if (
            set(template) != {"schema_version", "profiles", "managed_paths", "values"}
            or type(template["schema_version"]) is not int or template["schema_version"] != 1
            or template["profiles"] != list(PROFILES)
            or template["managed_paths"] != list(MANAGED_PATHS)
            or not isinstance(template["values"], dict)
            or set(template["values"]) != set(MANAGED_PATHS)
            or _has_secret_literal(template["values"])
        ):
            raise ValueError("invalid_schema")
        return template["values"], []
    except Exception:
        return None, [_finding("template", "template", "invalid_template")]


def check(root: Path, template: Path) -> tuple[int, list[dict]]:
    expected, findings = load_template(template)
    if expected is None:
        return 2, findings
    snapshots, errors = load_profiles(root)
    findings.extend(errors)
    for profile in PROFILES:
        for field, value in snapshots.get(profile, {}).items():
            # JSON encoding distinguishes YAML bool/int scalar types as well as values.
            if json.dumps(value, sort_keys=True) != json.dumps(expected[field], sort_keys=True):
                findings.append(_finding(profile, field, "changed"))
    if any(f["issue"] not in {"changed", "missing"} for f in findings):
        return 2, findings
    return (1 if findings else 0), findings


def generate_template(root: Path, destination: Path) -> tuple[int, list[dict]]:
    try:
        destination = destination.resolve()
        if not destination.is_relative_to(STAGING_ROOT) or destination.suffix.casefold() != ".json":
            return 2, [_finding("template", "template", "outside_staging")]
    except (OSError, ValueError, RuntimeError):
        return 2, [_finding("template", "template", "outside_staging")]
    snapshots, findings = load_profiles(root)
    reference = snapshots.get(PROFILES[0], {})
    for profile in PROFILES[1:]:
        for field in MANAGED_PATHS:
            if field in reference and field in snapshots.get(profile, {}):
                if json.dumps(reference[field], sort_keys=True) != json.dumps(snapshots[profile][field], sort_keys=True):
                    findings.append(_finding(profile, field, "changed"))
    if findings or len(snapshots) != len(PROFILES):
        return 2, findings
    data = {"schema_version": 1, "profiles": list(PROFILES), "managed_paths": list(MANAGED_PATHS), "values": reference}
    try:
        # No directory creation and no overwrite. Profiles are NEVER opened for writing.
        with destination.open("x", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    except FileExistsError:
        return 2, [_finding("template", "template", "already_exists")]
    except OSError:
        return 2, [_finding("template", "template", "write_failed")]
    return 0, []


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("invalid_arguments")


def main(argv=None) -> int:
    parser = _Parser(description="Report common-field DFIR config drift without printing values or repairing configs.")
    parser.add_argument("--profiles-root", type=Path, default=DEFAULT_PROFILES_ROOT)
    parser.add_argument("--template", type=Path, default=STAGING_ROOT / "common-config-template.json")
    parser.add_argument("--generate-template", action="store_true", help="Create a NEW common snapshot in the staged directory only.")
    try:
        args = parser.parse_args(argv)
        if args.generate_template:
            rc, findings = generate_template(args.profiles_root, args.template)
        else:
            rc, findings = check(args.profiles_root, args.template)
    except Exception:
        rc, findings = 2, [_finding("input", "input", "check_failed")]
    print(json.dumps({"status": {0: "ok", 1: "drift", 2: "error"}[rc], "findings": findings}, ensure_ascii=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
