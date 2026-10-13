"""Publish only the committed static payload to gh-pages, without changing main."""

import argparse
import os
import subprocess
import uuid
from pathlib import Path

from scripts.prepare_pages import FILES

ROOT = Path(__file__).resolve().parents[1]


def git(*args, input_bytes=None, env=None):
    return (
        subprocess.check_output(["git", *args], cwd=ROOT, input=input_bytes, env=env)
        .decode()
        .strip()
    )


def publish(source="HEAD"):
    source_commit = git("rev-parse", "--verify", f"{source}^{{commit}}")
    allowed = FILES | {"publish-manifest.json"}
    committed = set(git("ls-tree", "-r", "--name-only", f"{source_commit}:site").splitlines())
    if committed != allowed:
        raise ValueError("committed site differs from the approved public file allowlist")
    remote = git("ls-remote", "origin", "refs/heads/gh-pages")
    remote_old = remote.split()[0] if remote else None
    local_result = subprocess.run(
        ["git", "rev-parse", "--verify", "refs/heads/gh-pages"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    local_old = local_result.stdout.strip() if local_result.returncode == 0 else None
    if local_old and local_old != remote_old:
        raise ValueError("local gh-pages differs from origin; inspect before publishing")
    if remote_old:
        git("fetch", "origin", "gh-pages")
    data_root = (ROOT / "data").resolve()
    index_path = data_root / f"pages-index-{uuid.uuid4().hex}"
    if index_path.parent != data_root or index_path.exists():
        raise ValueError("unsafe temporary index path")
    data_root.mkdir(exist_ok=True)
    env = dict(os.environ, GIT_INDEX_FILE=str(index_path))
    try:
        git("read-tree", "--empty", env=env)
        for name in sorted(allowed):
            blob = git("rev-parse", f"{source_commit}:site/{name}")
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{name}", env=env)
        tree = git("write-tree", env=env)
        parents = ["-p", remote_old or source_commit]
        if remote_old:
            parents += ["-p", source_commit]
        commit = git(
            "commit-tree",
            tree,
            *parents,
            input_bytes=f"Publish verified research demo from {source_commit[:7]}\n".encode(),
        )
        git("update-ref", "refs/heads/gh-pages", commit, local_old or "0" * 40)
        git("push", "origin", "gh-pages")
        return source_commit, commit
    finally:
        if index_path.exists():
            index_path.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="HEAD", help="tested source commit containing site/")
    args = parser.parse_args()
    source, deployed = publish(args.source)
    print(f"source_commit={source}\npages_commit={deployed}")
