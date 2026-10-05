#!/usr/bin/env python3
"""离线应用的依赖与运行时入口回归检查；构建下载不受限制。"""

import argparse
import json
from pathlib import Path
import re
import subprocess
import tomllib


ROOT = Path(__file__).resolve().parent.parent
APPS = (
    "qingjian-cli",
    "qingjian-linux-server",
    "qingjian-macos",
    "qingjian-windows-server",
    "qingjian-windows-tsf",
    "qingjian-windows-settings",
)
BANNED = {
    "qingjian-predict", "qingjian-update", "reqwest", "async-openai", "ureq",
    "hyper", "hyper-util", "hyper-tls", "hyper-rustls", "http", "http-body",
    "http-body-util", "h2", "curl", "curl-sys", "isahc", "surf", "attohttpc",
    "ureq-proto", "aws-sdk-s3", "hf-hub",
}
PROTECTED = (
    "qingjian-core", "qingjian-dictionary", "qingjian-translate",
    "qingjian-learning", "qingjian-lm", "qingjian-neural", "qingjian-render",
)
# 不扫构建脚本、网页文档与保留的 upstream 网络 crate。
SOURCE_ROOTS = [ROOT / "apps" / app / "src" for app in ("cli", "macos")]
SOURCE_ROOTS += [ROOT / "apps/windows" / app / "src" for app in ("server", "tsf", "settings")]
SOURCE_ROOTS += [ROOT / "apps/linux/server/src", ROOT / "apps/linux/fcitx5/src"]
SOURCE_ROOTS += [ROOT / "crates" / name / "src" for name in (*PROTECTED, "qingjian-platform")]
NETWORK = re.compile(
    r"https?://|\b(?:reqwest|async_openai|ureq|hyper|webbrowser)\s*::"
    r"|\b(?:TcpStream|TcpListener|UdpSocket|AF_INET6?|WinHttp\w*|InternetOpen\w*|LaunchUri\w*)\b"
    r"|\b(?:curl|wget)\b"
)


def closure(start, graph):
    seen, pending = set(), [start]
    while pending:
        node = pending.pop()
        if node not in seen:
            seen.add(node)
            pending.extend(graph.get(node, ()))
    return seen


def check_lock():
    """锁文件跨平台、含 build/dev 的保守上界，防止间接依赖漏检。"""
    packages = tomllib.loads((ROOT / "Cargo.lock").read_text())["package"]
    graph = {}
    for package in packages:
        graph.setdefault(package["name"], set()).update(
            dependency.split()[0] for dependency in package.get("dependencies", ())
        )
    for app in APPS:
        if app not in graph:
            raise AssertionError(f"missing application: {app}")
        forbidden = closure(app, graph) & BANNED
        if forbidden:
            raise AssertionError(f"{app}: forbidden dependencies {sorted(forbidden)}")
        print(f"PASS lock: {app}")


def check_sources():
    failures = []
    for directory in SOURCE_ROOTS:
        for path in directory.rglob("*"):
            if "tests" in path.parts or path.name == "tests.rs":
                continue
            if path.suffix not in {".rs", ".cpp", ".h"}:
                continue
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                if NETWORK.search(line):
                    failures.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")
    installer = (ROOT / "apps/windows/installer/qingjian.iss").read_text()
    if re.search(r"https?://|App(?:Support|Updates|Publisher)URL", installer):
        failures.append("Windows installer has a web link")
    if failures:
        raise AssertionError("network source found:\n" + "\n".join(failures))
    print("PASS source: no HTTP client, Internet socket or external URL entry")


def check_metadata(target):
    """核对 Cargo 真正解析出的 target 依赖图，不以手改的 lock 替代解析。"""
    metadata = json.loads(subprocess.check_output([
        "cargo", "metadata", "--format-version", "1", "--locked",
        "--filter-platform", target,
    ], cwd=ROOT, text=True))
    packages = {package["id"]: package["name"] for package in metadata["packages"]}
    graph = {
        node["id"]: {
            dependency["pkg"] for dependency in node["deps"]
            if any(kind["kind"] is None for kind in dependency["dep_kinds"])
        }
        for node in metadata["resolve"]["nodes"]
    }
    for app in APPS:
        start = next(key for key, name in packages.items() if name == app)
        forbidden = {packages[key] for key in closure(start, graph)} & BANNED
        if forbidden:
            raise AssertionError(f"{target}/{app}: {sorted(forbidden)}")
    print(f"PASS Cargo metadata: {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", action="append", default=[])
    args = parser.parse_args()
    check_lock()
    check_sources()
    for target in args.target:
        check_metadata(target)
