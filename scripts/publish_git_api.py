"""Transfer one ordinary fast-forward commit over GitHub's API when Git HTTPS is blocked.

Uses the repository credential helper in memory. No tokens are logged or saved.
Creates the exact local blobs/tree/commit, verifies every SHA, then moves main with force=false.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import subprocess
import urllib.error
import urllib.request

REPO = "dreamingto/AIC-9.2"


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-parent", required=True)
    args = parser.parse_args()
    head = git("rev-parse", "HEAD").decode().strip()
    parent = git("rev-parse", "HEAD^").decode().strip()
    if parent != args.expected_parent or git("rev-parse", "--abbrev-ref", "HEAD").strip() != b"main":
        raise SystemExit("Only the specified single main fast-forward commit is supported")
    credential = subprocess.run(["git", "credential", "fill"], input=b"protocol=https\nhost=github.com\npath=dreamingto/AIC-9.2.git\n\n", capture_output=True, check=True)
    fields = dict(line.split("=", 1) for line in credential.stdout.decode().splitlines() if "=" in line)
    token = fields.get("password")
    if not token:
        raise SystemExit("No repository credential available")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def api(route: str, payload=None, method: str | None = None):
        request = urllib.request.Request("https://api.github.com/repos/" + REPO + route,
            data=json.dumps(payload).encode() if payload is not None else None,
            method=method,
            headers={"Authorization":"Bearer " + token, "Accept":"application/vnd.github+json", "User-Agent":"jitu-release", "Content-Type":"application/json"})
        try:
            with opener.open(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            # Deliberately exclude request headers and credential objects.
            raise RuntimeError(f"GitHub API {exc.code} for {route}") from None

    remote = api("/git/ref/heads/main")["object"]["sha"]
    if remote == head:
        print(json.dumps({"sha":head,"status":"already_synced"})); return
    if remote != parent:
        raise SystemExit("Remote main moved; refusing to overwrite another commit")
    expected_tree = git("rev-parse", "HEAD^{tree}").decode().strip()
    changed = git("diff-tree", "--no-commit-id", "--name-only", "-z", "-r", parent, head).decode().split("\0")
    paths = [p for p in changed if p]
    tree = {}
    for entry in git("ls-tree", "-rz", "HEAD").split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            mode, kind, sha = metadata.decode().split()
            tree[name.decode()] = (mode,kind,sha)

    def upload(path: str):
        if path not in tree:
            return {"path":path,"mode":"100644","type":"blob","sha":None}
        mode, kind, sha = tree[path]
        if kind != "blob":
            raise ValueError("Submodules are not supported")
        content = git("cat-file", "blob", sha)
        if len(content) > 10*1024*1024:
            raise ValueError("Large artifact must use a release asset")
        try:
            # Git trees accept UTF-8 content inline, avoiding hundreds of content-write calls.
            return {"path":path,"mode":mode,"type":"blob","content":content.decode("utf-8")}
        except UnicodeDecodeError:
            pass
        created = api("/git/blobs", {"content":base64.b64encode(content).decode(),"encoding":"base64"})
        if created["sha"] != sha:
            raise ValueError("Blob identity mismatch")
        return {"path":path,"mode":mode,"type":"blob","sha":sha}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        entries = list(pool.map(upload, paths))
    base_tree = api("/git/commits/" + parent)["tree"]["sha"]
    created_tree = api("/git/trees", {"base_tree":base_tree,"tree":entries})
    if created_tree["sha"] != expected_tree:
        raise SystemExit("Tree identity mismatch; main was not changed")
    raw = git("cat-file", "commit", head).decode()
    headers, message = raw.split("\n\n",1)
    if any(h.startswith(("gpgsig ","encoding ")) for h in headers.splitlines()):
        raise SystemExit("Signed/non-default commits need native Git transfer")
    def identity(kind: str):
        fmt = "%an%x00%ae%x00%aI" if kind == "author" else "%cn%x00%ce%x00%cI"
        name,email,date = git("show","-s","--format="+fmt,head).decode().strip().split("\0")
        return {"name":name,"email":email,"date":date}
    created_commit = api("/git/commits", {"message":message,"tree":expected_tree,"parents":[parent],"author":identity("author"),"committer":identity("committer")})
    if created_commit["sha"] != head:
        raise SystemExit("Commit identity mismatch; main was not changed")
    # force=false is an atomic non-destructive fast-forward check at GitHub.
    updated = api("/git/refs/heads/main", {"sha":head,"force":False}, "PATCH")
    if updated["object"]["sha"] != head:
        raise SystemExit("Remote update verification failed")
    subprocess.run(["git","update-ref","refs/remotes/origin/main",head,parent],check=True)
    print(json.dumps({"sha":head,"tree":expected_tree,"transferred_files":len(paths),"force":False}))


if __name__ == "__main__":
    main()
