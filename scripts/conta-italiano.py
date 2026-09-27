r"""Count Italian-language lines in our own code, per area (English port progress meter).

Heuristic: a line counts as Italian when it holds at least two common Italian function words. It
misses single-word labels and Italian identifiers, so treat the numbers as a trend, not a census.

Scope per repository:
- forks (odysseus, shadowbroker): only files we added or changed against the upstream branch;
- our own repositories: every tracked file.

Usage:
  py scripts\conta-italiano.py                       (default repositories under D:\assistenteeee)
  py scripts\conta-italiano.py --repo D:\vergilius-lab\porting-en\odysseus --base origin/dev
  py scripts\conta-italiano.py --json out.json --files    (per-file detail as well)

Baseline measured on 2026-09-28 (before the English port): odysseus 1600 lines in 160 files,
shadowbroker 71 in 23, root repository 1056 in 140 (scripts 830, biblioteca-skill 88, voce 62).
"""
import argparse
import collections
import json
import os
import re
import subprocess

ITALIAN = re.compile(
    r"\b(che|della|delle|degli|dello|perch[eé]|questo|questa|questi|sono|viene|nella|nelle|nel|alla|alle|dell"
    r"|gi[aà]|pu[oò]|pi[uù]|anche|quando|senza|oppure|ogni|essere|deve|fatto|come|dopo|prima|cosa)\b",
    re.IGNORECASE,
)
BINARY = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".onnx", ".bin", ".gguf", ".moc3",
          ".lock", ".svg", ".pdf", ".zip", ".wav", ".mp3", ".gz", ".webp", ".exe", ".dll")
DEFAULTS = [
    (r"D:\assistenteeee\odysseus", "origin/dev", 2),
    (r"D:\assistenteeee\shadowbroker", "origin/main", 2),
    (r"D:\assistenteeee", None, 1),
]


def git_files(repo, base):
    if base:
        mb = subprocess.run(["git", "-C", repo, "merge-base", "HEAD", base], capture_output=True, text=True, check=True)
        cmd = ["git", "-C", repo, "diff", "--name-only", "--diff-filter=AMR", mb.stdout.strip(), "HEAD"]
    else:
        cmd = ["git", "-C", repo, "ls-files"]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return [r for r in out.splitlines() if r.strip()]


def count(repo, base, depth, per_file):
    lines, files, detail = collections.Counter(), collections.Counter(), {}
    for rel in git_files(repo, base):
        path = os.path.join(repo, rel)
        if rel.lower().endswith(BINARY) or not os.path.isfile(path) or os.path.getsize(path) > 2_000_000:
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                n = sum(1 for row in f if len(ITALIAN.findall(row)) >= 2)
        except OSError:
            continue
        if n:
            area = "/".join(rel.split("/")[:depth])
            lines[area] += n
            files[area] += 1
            if per_file:
                detail[rel] = n
    return lines, files, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", help="repository or worktree path (default: our three repositories)")
    ap.add_argument("--base", help="upstream ref for forks; omit to scan every tracked file")
    ap.add_argument("--depth", type=int, default=2, help="path depth used to group areas")
    ap.add_argument("--files", action="store_true", help="also report per-file counts")
    ap.add_argument("--json", help="write the result to this JSON file")
    a = ap.parse_args()
    targets = [(a.repo, a.base, a.depth)] if a.repo else DEFAULTS
    result = {}
    for repo, base, depth in targets:
        lines, files, detail = count(repo, base, depth, a.files)
        result[repo] = {"lines": sum(lines.values()), "files": sum(files.values()),
                        "areas": {k: {"lines": v, "files": files[k]} for k, v in lines.most_common()}}
        if a.files:
            result[repo]["per_file"] = dict(sorted(detail.items(), key=lambda kv: -kv[1]))
        print(f"== {repo}: {sum(lines.values())} Italian lines in {sum(files.values())} files")
        for k, v in lines.most_common(25):
            print(f"   {v:6d} {files[k]:4d}  {k}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
