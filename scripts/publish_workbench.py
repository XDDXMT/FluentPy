"""Publish the checked portable bundle as GitHub Release assets, never in Git."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tomllib
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "XDDXMT/FluentPy"
API = "https://api.github.com/repos/" + REPOSITORY


def api(url, *, method="GET", payload=None, token=None, content_type="application/json"):
    if urlsplit(url).hostname not in ("api.github.com", "uploads.github.com"):
        raise ValueError("Unexpected GitHub API host")
    headers = {"User-Agent": "FluentPy-workbench-publisher", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if isinstance(payload, dict):
        payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if payload is not None:
        headers["Content-Type"] = content_type
    request = Request(url, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=180) as response:
            return json.load(response)
    except HTTPError as error:
        if method == "GET" and error.code == 404:
            return None
        raise RuntimeError(f"GitHub API {method} failed with HTTP {error.code}") from None


def credential():
    environment = os.environ.copy()
    environment.update(GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
    result = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                            text=True, capture_output=True, env=environment, cwd=ROOT)
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if result.returncode or not fields.get("password"):
        raise RuntimeError("GitHub credentials are unavailable in the existing Git credential manager.")
    return fields["password"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload", action="store_true", help="Upload and publish the checked release")
    args = parser.parse_args()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    folder = ROOT / "dist/workbench" / version
    manifest = json.loads((folder / "workbench-release.json").read_text(encoding="utf-8"))
    archive = folder / manifest["file"]
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assert digest == manifest["sha256"] and archive.stat().st_size == manifest["size"]
    assets = [archive, folder / "SHA256SUMS.txt", folder / "workbench-release.json"]
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in assets}
    tag = "v" + version
    if not args.upload:
        release = api(API + "/releases/tags/" + tag)
        print(json.dumps({"version": version, "local_files": hashes,
                          "release": release["html_url"] if release else None}, indent=2))
        return
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise RuntimeError("Commit the reviewed source before publishing.")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    token = credential()
    release = api(API + "/releases/tags/" + tag, token=token)
    if release is None:
        body = (f"FluentPy {version} Windows x64 便携工作台。\n\n"
                f"下载 `{archive.name}`，解压整个文件夹后双击 `FluentPy-Workbench.exe`。无需安装 Python，无需管理员权限。\n\n"
                "包含原生 Qt 工作台、独立代码编辑器、性能对照、八组 C 后端和 107 个图标。请保留 `_internal` 文件夹；许可证与第三方声明随包提供。\n\n"
                "`SHA256SUMS.txt` 提供完整性校验。组件库仍可通过 `python -m pip install -U fluentpy-qt` 安装。\n\n"
                "文档：https://fluentpy.mcxmcl.cn/")
        release = api(API + "/releases", method="POST", token=token, payload={"tag_name": tag,
                      "target_commitish": commit, "name": f"FluentPy {version} · Windows 工作台", "body": body, "draft": True, "prerelease": False})
    upload_url = release["upload_url"].split("{", 1)[0]
    existing = {item["name"]: item for item in release["assets"]}
    for path in assets:
        if path.name in existing:
            asset = existing[path.name]
        else:
            asset = api(upload_url + "?name=" + quote(path.name), method="POST", token=token,
                        payload=path.read_bytes(), content_type="application/zip" if path.suffix == ".zip" else "application/octet-stream")
        if asset.get("digest") != "sha256:" + hashes[path.name] or asset["size"] != path.stat().st_size:
            raise RuntimeError("Public asset checksum does not match: " + path.name)
        print("Verified GitHub asset: " + path.name, flush=True)
    if release["draft"]:
        release = api(API + "/releases/" + str(release["id"]), method="PATCH", token=token,
                      payload={"draft": False, "make_latest": "true"})
    public = api(API + "/releases/tags/" + tag)
    assert public and not public["draft"]
    public_files = {item["name"]: item for item in public["assets"]}
    for name, checksum in hashes.items():
        assert public_files[name]["digest"] == "sha256:" + checksum
    print(json.dumps({"release": public["html_url"], "download": public_files[archive.name]["browser_download_url"],
                      "sha256": digest, "size": archive.stat().st_size}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
