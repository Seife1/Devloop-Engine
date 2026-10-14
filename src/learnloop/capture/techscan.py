"""Deterministic technologies and dependency scanning for LearnLoop projects.

Standard library only: tomllib, json, re, pathlib, os, sys, stat, urllib.parse.
Offline, instant, zero external processes or network risk, zero credential leakage.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
import tomllib
from pathlib import Path
from typing import Any, TypedDict

MAX_DEPTH = 2
MAX_VISITED_FILES = 2000
MAX_FILE_SIZE_BYTES = 200 * 1024  # 200 KB
MAX_TECHNOLOGIES_PER_PROJECT = 200

SKIP_DIR_NAMES = {
    "node_modules",
    "venv",
    ".venv",
    "vendor",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
}

PYTHON_NAME_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$")
NPM_NAME_REGEX = re.compile(r"^(@[a-zA-Z0-9_.-]+/)?[a-zA-Z0-9_.-]+$")
GO_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)*$")
CARGO_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")
DOCKER_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.-]+)*$")

SCHEME_PREFIXES = ("http://", "https://", "git://", "git+http://", "git+https://", "ssh://", "ftp://")


class DetectedTechnology(TypedDict):
    ecosystem: str
    name: str
    version_spec: str | None
    source_file: str


def redact_credentials(text: str) -> str:
    """Redact user:pass or user credentials from URLs and connection strings."""
    if not text:
        return ""
    return re.sub(
        r"([a-zA-Z][a-zA-Z0-9+.-]*://)([^/@\s:]+)(?::([^/@\s]+))?@",
        r"\1***@",
        text,
    )


def is_reparse_point_or_link(path: Path | str) -> bool:
    """Return True if path is a symlink, Windows junction, or reparse point."""
    try:
        p = Path(path)
        if p.is_symlink() or os.path.islink(p):
            return True
        st = p.lstat()
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        attrs = getattr(st, "st_file_attributes", 0)
        if bool(attrs & reparse_flag):
            return True
        return False
    except (OSError, ValueError):
        return True


def _clean_version_spec(spec: str | None) -> str | None:
    if not spec:
        return None
    cleaned = redact_credentials(spec.strip())
    # Strip any surrounding quotes or whitespace
    cleaned = cleaned.strip("\"' \t\r\n")
    if not cleaned:
        return None
    return cleaned[:60]


def parse_requirements_txt(content: str, source_file: str) -> list[DetectedTechnology]:
    """Parse requirements*.txt without storing URLs or options, redacting credentials."""
    results: list[DetectedTechnology] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Strip inline comments
        if " #" in line:
            line = line.split(" #", 1)[0].strip()

        # Option lines: -r, -e, -i, -f, --index-url, --extra-index-url, etc.
        if line.startswith("-"):
            # Option lines must be ignored; never store URLs as package names
            continue

        # Strip environment markers (; sys_platform == ...)
        if ";" in line:
            line = line.split(";", 1)[0].strip()

        # Check for direct URL dependency: pkg @ https://...
        if "@" in line:
            parts = line.split("@", 1)
            name_candidate = parts[0].strip()
            # Strip extras [foo]
            name_candidate = re.sub(r"\[.*?\]", "", name_candidate).strip()
            if PYTHON_NAME_REGEX.match(name_candidate) and len(name_candidate) <= 100:
                results.append({
                    "ecosystem": "python",
                    "name": name_candidate,
                    "version_spec": None,
                    "source_file": source_file,
                })
            continue

        # Check if line is an unadorned URL (drop it)
        if any(line.lower().startswith(p) for p in SCHEME_PREFIXES):
            continue

        # Standard requirement line: name[extras] (==1.0, >=2.0)
        m = re.match(r"^([a-zA-Z0-9_.\-]+)(?:\[[^\]]*\])?\s*(.*)$", line)
        if not m:
            continue

        name = m.group(1).strip()
        spec = m.group(2).strip()

        if not PYTHON_NAME_REGEX.match(name) or len(name) > 100:
            continue
        if name.lower() in ("http", "https", "git", "ssh", "ftp"):
            continue

        version_spec = _clean_version_spec(spec)
        results.append({
            "ecosystem": "python",
            "name": name,
            "version_spec": version_spec,
            "source_file": source_file,
        })
    return results


def parse_pyproject_toml(content: str, source_file: str) -> list[DetectedTechnology]:
    """Parse pyproject.toml [project] dependencies and optional-dependencies."""
    try:
        data = tomllib.loads(content)
    except Exception as exc:
        sys.stderr.write(f"Warning: could not parse pyproject.toml ({source_file}): {exc}\n")
        return []

    project = data.get("project", {})
    dep_strings: list[str] = []

    # Main dependencies
    main_deps = project.get("dependencies", [])
    if isinstance(main_deps, list):
        for item in main_deps:
            if isinstance(item, str):
                dep_strings.append(item)

    # Optional dependencies
    opt_deps = project.get("optional-dependencies", {})
    if isinstance(opt_deps, dict):
        for group in opt_deps.values():
            if isinstance(group, list):
                for item in group:
                    if isinstance(item, str):
                        dep_strings.append(item)

    # Build-system requirements
    build_sys = data.get("build-system", {})
    reqs = build_sys.get("requires", [])
    if isinstance(reqs, list):
        for item in reqs:
            if isinstance(item, str):
                dep_strings.append(item)

    # Parse each dep string using the requirements parser logic
    fake_req_content = "\n".join(dep_strings)
    return parse_requirements_txt(fake_req_content, source_file)


def parse_package_json(content: str, source_file: str) -> list[DetectedTechnology]:
    """Parse package.json dependencies, devDependencies, and peerDependencies."""
    results: list[DetectedTechnology] = []
    try:
        data = json.loads(content)
    except Exception as exc:
        sys.stderr.write(f"Warning: could not parse package.json ({source_file}): {exc}\n")
        return []

    if not isinstance(data, dict):
        return []

    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps = data.get(section, {})
        if isinstance(deps, dict):
            for name, spec in deps.items():
                if not isinstance(name, str):
                    continue
                name_clean = name.strip()
                if not NPM_NAME_REGEX.match(name_clean) or len(name_clean) > 100:
                    continue
                spec_str = str(spec) if spec is not None else None
                version_spec = _clean_version_spec(spec_str)
                results.append({
                    "ecosystem": "npm",
                    "name": name_clean,
                    "version_spec": version_spec,
                    "source_file": source_file,
                })
    return results


def parse_go_mod(content: str, source_file: str) -> list[DetectedTechnology]:
    """Parse go.mod direct and indirect requirements."""
    results: list[DetectedTechnology] = []
    in_require_block = False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        if line == "require (" or line.startswith("require ("):
            in_require_block = True
            continue
        if in_require_block and line.startswith(")"):
            in_require_block = False
            continue

        # Strip inline comments
        if "//" in line:
            line = line.split("//", 1)[0].strip()

        tokens = line.split()
        if in_require_block:
            if len(tokens) >= 2:
                mod_name, version = tokens[0], tokens[1]
                if GO_NAME_REGEX.match(mod_name) and len(mod_name) <= 100:
                    results.append({
                        "ecosystem": "go",
                        "name": mod_name,
                        "version_spec": _clean_version_spec(version),
                        "source_file": source_file,
                    })
        elif line.startswith("require ") and len(tokens) >= 3:
            mod_name, version = tokens[1], tokens[2]
            if GO_NAME_REGEX.match(mod_name) and len(mod_name) <= 100:
                results.append({
                    "ecosystem": "go",
                    "name": mod_name,
                    "version_spec": _clean_version_spec(version),
                    "source_file": source_file,
                })
    return results


def parse_cargo_toml(content: str, source_file: str) -> list[DetectedTechnology]:
    """Parse Cargo.toml [dependencies], [dev-dependencies], and [build-dependencies]."""
    results: list[DetectedTechnology] = []
    try:
        data = tomllib.loads(content)
    except Exception as exc:
        sys.stderr.write(f"Warning: could not parse Cargo.toml ({source_file}): {exc}\n")
        return []

    sections = ("dependencies", "dev-dependencies", "build-dependencies", "workspace.dependencies")
    for sec in sections:
        table: Any = data
        for part in sec.split("."):
            if isinstance(table, dict):
                table = table.get(part, {})
            else:
                table = {}
        if isinstance(table, dict):
            for name, val in table.items():
                if not isinstance(name, str):
                    continue
                name_clean = name.strip()
                if not CARGO_NAME_REGEX.match(name_clean) or len(name_clean) > 100:
                    continue

                version_spec: str | None = None
                if isinstance(val, str):
                    version_spec = _clean_version_spec(val)
                elif isinstance(val, dict):
                    v = val.get("version")
                    if isinstance(v, str):
                        version_spec = _clean_version_spec(v)
                    elif "git" in val:
                        version_spec = _clean_version_spec("git")
                    elif "path" in val:
                        version_spec = _clean_version_spec("path")

                results.append({
                    "ecosystem": "cargo",
                    "name": name_clean,
                    "version_spec": version_spec,
                    "source_file": source_file,
                })
    return results


def parse_dockerfile(content: str, source_file: str) -> list[DetectedTechnology]:
    """Parse Dockerfile FROM instructions for base images."""
    results: list[DetectedTechnology] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^FROM\s+(?:--platform=\S+\s+)?([^\s]+)(?:\s+[aA][sS]\s+\S+)?", line)
        if not m:
            continue
        image_spec = m.group(1).strip()
        if not image_spec or image_spec.lower() == "scratch":
            results.append({
                "ecosystem": "docker",
                "name": "scratch",
                "version_spec": None,
                "source_file": source_file,
            })
            continue

        if ":" in image_spec:
            img_name, tag = image_spec.split(":", 1)
        else:
            img_name, tag = image_spec, None

        if DOCKER_NAME_REGEX.match(img_name) and len(img_name) <= 100:
            results.append({
                "ecosystem": "docker",
                "name": img_name,
                "version_spec": _clean_version_spec(tag),
                "source_file": source_file,
            })
    return results


def parse_docker_compose(content: str, source_file: str) -> list[DetectedTechnology]:
    """Parse docker-compose*.yml / yaml service images without external libraries."""
    results: list[DetectedTechnology] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^image:\s+[\"']?([^\s\"']+)[\"']?", line)
        if not m:
            continue
        image_spec = m.group(1).strip()
        if ":" in image_spec:
            img_name, tag = image_spec.split(":", 1)
        else:
            img_name, tag = image_spec, None

        if DOCKER_NAME_REGEX.match(img_name) and len(img_name) <= 100:
            results.append({
                "ecosystem": "docker",
                "name": img_name,
                "version_spec": _clean_version_spec(tag),
                "source_file": source_file,
            })
    return results


def scan_technologies(repo_path: Path | str) -> list[DetectedTechnology]:
    """Scan a repository directory deterministically up to depth 2 for project technologies.

    Safe against symlink/reparse-point escapes, oversized files, and credential leakage.
    """
    try:
        raw_path = Path(repo_path)
        if is_reparse_point_or_link(raw_path):
            return []
        resolved_repo = raw_path.resolve()
        if not resolved_repo.exists() or not resolved_repo.is_dir():
            return []
        if is_reparse_point_or_link(resolved_repo):
            return []
    except Exception:
        return []

    visited_count = 0
    all_detected: list[DetectedTechnology] = []

    # BFS or directory traversal limited to depth <= MAX_DEPTH
    # Queue stores: (current_dir, depth)
    queue: list[tuple[Path, int]] = [(resolved_repo, 0)]

    while queue and visited_count < MAX_VISITED_FILES:
        current_dir, depth = queue.pop(0)

        try:
            entries = list(current_dir.iterdir())
        except (OSError, PermissionError):
            continue

        # Sort entries deterministically
        entries.sort(key=lambda p: p.name.lower())

        for entry in entries:
            visited_count += 1
            if visited_count > MAX_VISITED_FILES:
                break

            name_lower = entry.name.lower()

            # Skip symlinks, junctions, reparse points
            if is_reparse_point_or_link(entry):
                continue

            # Verify resolved path is strictly within repo
            try:
                resolved_entry = entry.resolve()
                if not resolved_entry.is_relative_to(resolved_repo):
                    continue
                if is_reparse_point_or_link(resolved_entry):
                    continue
            except Exception:
                continue

            if entry.is_dir():
                if name_lower in SKIP_DIR_NAMES or name_lower.startswith("."):
                    continue
                if depth < MAX_DEPTH:
                    queue.append((entry, depth + 1))
                continue

            if not entry.is_file():
                continue

            # File size limit
            try:
                st = entry.stat()
                if st.st_size > MAX_FILE_SIZE_BYTES or st.st_size == 0:
                    continue
            except (OSError, PermissionError):
                continue

            rel_source = str(entry.relative_to(resolved_repo)).replace("\\", "/")

            # Read text safely
            try:
                content = entry.read_text("utf-8", errors="replace")
            except Exception as exc:
                sys.stderr.write(f"Warning: could not read {rel_source}: {exc}\n")
                continue

            # Match and parse
            if re.match(r"^requirements.*\.txt$", name_lower):
                all_detected.extend(parse_requirements_txt(content, rel_source))
            elif name_lower == "pyproject.toml":
                all_detected.extend(parse_pyproject_toml(content, rel_source))
            elif name_lower == "package.json":
                all_detected.extend(parse_package_json(content, rel_source))
            elif name_lower == "go.mod":
                all_detected.extend(parse_go_mod(content, rel_source))
            elif name_lower == "cargo.toml":
                all_detected.extend(parse_cargo_toml(content, rel_source))
            elif name_lower == "dockerfile" or name_lower.startswith("dockerfile."):
                all_detected.extend(parse_dockerfile(content, rel_source))
            elif re.match(r"^docker-compose.*\.ya?ml$", name_lower):
                all_detected.extend(parse_docker_compose(content, rel_source))

    # Deduplicate by (ecosystem, name), preserving earliest discovered version_spec
    deduped: dict[tuple[str, str], DetectedTechnology] = {}
    for tech in all_detected:
        key = (tech["ecosystem"], tech["name"])
        if key not in deduped:
            deduped[key] = tech
        elif deduped[key]["version_spec"] is None and tech["version_spec"] is not None:
            deduped[key] = tech

    final_list = sorted(deduped.values(), key=lambda t: (t["ecosystem"], t["name"]))
    return final_list[:MAX_TECHNOLOGIES_PER_PROJECT]
