"""Vendor missing 24px Regular SVGs from a pinned Microsoft MIT snapshot.

Existing assets and public enum names are preserved. Run with a reviewed full
commit hash; no upstream Python or build scripts are imported or executed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src/fluentpy/assets/icons"
REPOSITORY = "https://github.com/microsoft/fluentui-system-icons"
API = "https://api.github.com/repos/microsoft/fluentui-system-icons"


def request(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "FluentPy-icon-vendor"}), timeout=120
    )


def json_request(path):
    with request(API + path) as response:
        return json.load(response)


def enum_entries(source):
    cls = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.ClassDef) and node.name == "FluentIcon"
    )
    entries = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in cls.body
        if isinstance(node, ast.Assign)
    }
    return cls, entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--cache", type=Path, default=ROOT / "build/icon-cache")
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{40}", args.commit) is None:
        parser.error("review and supply a complete upstream commit hash")
    audit = args.cache.resolve()
    audit.mkdir(parents=True, exist_ok=True)
    tree_file = audit / "upstream-tree.json"
    if tree_file.exists() and json.loads(tree_file.read_text("utf-8"))["commit"] == args.commit:
        tree = json.loads(tree_file.read_text("utf-8"))
    else:
        root = json_request("/git/trees/" + args.commit)
        assets = next(item for item in root["tree"] if item["path"] == "assets")
        tree = json_request("/git/trees/" + assets["sha"] + "?recursive=1")
    if tree.get("truncated"):
        raise RuntimeError("upstream inventory is truncated; refusing an incomplete import")
    expected = {
        "assets/" + item["path"]: item
        for item in tree["tree"]
        if item["path"].endswith("_24_regular.svg")
    }
    snapshot = audit / f"{args.commit}.tar.gz"
    if not snapshot.exists():
        print(f"Downloading the official pinned snapshot {args.commit}...", flush=True)
        temporary = snapshot.with_suffix(".download")
        with (
            request(
                f"https://codeload.github.com/microsoft/fluentui-system-icons/tar.gz/{args.commit}"
            ) as response,
            temporary.open("wb") as output,
        ):
            shutil.copyfileobj(response, output)
        temporary.rename(snapshot)
    print(f"Inspecting {len(expected)} 24px Regular icons...", flush=True)
    entries = {}
    license_data = notice_data = None
    added = 0
    with tarfile.open(snapshot) as archive:
        for member in archive:
            if not member.isfile():
                continue
            relative = member.name.partition("/")[2]
            if relative not in expected and relative not in {"LICENSE", "NOTICE"}:
                continue
            data = archive.extractfile(member).read()
            if relative == "LICENSE":
                license_data = data
                continue
            if relative == "NOTICE":
                notice_data = data
                continue
            blob = hashlib.sha1(
                b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            ).hexdigest()
            if blob != expected[relative]["sha"]:
                raise RuntimeError(f"upstream Git blob mismatch: {relative}")
            svg = ET.fromstring(data)
            if svg.tag != "{http://www.w3.org/2000/svg}svg" or svg.attrib.get("viewBox") not in {
                "0 0 24 24",
                "0 0 25 24",
            }:
                raise ValueError(f"unexpected SVG: {relative}")
            if any(
                node.tag.rsplit("}", 1)[-1] in {"script", "foreignObject", "image"}
                for node in svg.iter()
            ):
                raise ValueError(f"non-vector content: {relative}")
            parts = Path(relative).parts
            filename = parts[-1]
            if len(parts) > 4:
                # Upstream gives localized glyphs the same basename. Keep each
                # variant, using e.g. TEXT_BOLD_RU without overwriting TEXT_BOLD.
                locale = "_".join(parts[2:-2]).replace("-", "_")
                filename = filename.replace("_24_regular.svg", f"_{locale}_24_regular.svg")
            destination = ASSETS / filename
            if not destination.exists():
                destination.write_bytes(data)
                added += 1
            actual = destination.read_bytes()
            entries[destination.name] = {
                "viewBox": svg.attrib["viewBox"],
                "upstream_path": relative,
                "sha256": hashlib.sha256(actual).hexdigest(),
                "upstream_git_blob": blob,
                "matches_snapshot": actual == data,
            }
    if len(entries) != len(expected) or license_data is None or b"MIT License" not in license_data:
        raise RuntimeError("incomplete snapshot or missing MIT license")
    license_path = ROOT / "licenses/Microsoft-Fluent-System-Icons-LICENSE.txt"
    if license_path.read_bytes().replace(b"\r\n", b"\n") != license_data.replace(b"\r\n", b"\n"):
        raise RuntimeError(
            "the upstream license changed; review before replacing the retained license"
        )
    if notice_data is not None:
        (ROOT / "licenses/Microsoft-Fluent-System-Icons-NOTICE.txt").write_bytes(notice_data)
    module = ROOT / "src/fluentpy/icons.py"
    source = module.read_text("utf-8")
    cls, names = enum_entries(source)
    additions = []
    for filename, entry in sorted(entries.items()):
        name = next((key for key, value in names.items() if value == filename), None)
        if name is None:
            name = filename.removeprefix("ic_fluent_").removesuffix("_24_regular.svg").upper()
            if not name.isidentifier():
                name = "ICON_" + name
            if name in names:
                name = "MICROSOFT_" + name
            if name in names:
                raise ValueError(f"enum name collision: {name}")
            additions.append(f'    {name} = "{filename}"\n')
            names[name] = filename
        entry["enum"] = name
    if additions:
        lines = source.splitlines(keepends=True)
        lines[cls.end_lineno : cls.end_lineno] = [
            "\n    # Pinned upstream 24px Regular catalog; maintained by scripts/sync_icons.py.\n",
            *additions,
        ]
        module.write_text("".join(lines), encoding="utf-8", newline="\n")
    manifest = {
        "repository": REPOSITORY,
        "commit": args.commit,
        "style": "24px Regular, including localized variants; without duplicate sizes or Filled variants",
        "license": "MIT",
        "license_sha256": hashlib.sha256(license_path.read_bytes()).hexdigest(),
        "icons": entries,
    }
    (ASSETS / "UPSTREAM.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Added {added} original SVGs; {len(entries)} Microsoft icons, {len(names)} total public icons; existing assets preserved.",
        flush=True,
    )


if __name__ == "__main__":
    main()
