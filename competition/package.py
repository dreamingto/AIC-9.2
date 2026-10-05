"""Freeze reviewed artifacts as a separate anonymous preview package with SHA256 inventory."""
import hashlib
import json
import zipfile
from pathlib import Path

from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT / "output/competition"
DEST=Path("D:/codex-releases/AIC-9.2")
names=["机图索隐_技术报告.pdf","机图索隐_答辩幻灯片.pdf","机图索隐_真实系统演示.mp4","答辩幻灯片.html","deck.css","项目简介.txt","演示逐字稿.md","comparison.json","comparison.md","corpus-lock.json","function-evidence-drafts.json","function-evidence-drafts.md","live-demo-response.json"]
files=[OUT / n for n in names] + list((OUT/"vendor").glob("*"))
files += [OUT/"assets"/(key+".jpg") for key in ("ai-zhsy-p24-loom","ai-zhsy-p26-large-loom","ai-nlc-p25-water-pestle","ai-nlc-p26-water-mill")]
assert all(p.is_file() for p in files)
assert len(PdfReader(OUT/names[0]).pages)==8
assert len(PdfReader(OUT/names[1]).pages)==8
assert (OUT/names[0]).stat().st_size<=10*1024*1024
assert (OUT/names[2]).stat().st_size<=300*1024*1024
manifest={"format":"jitu-competition-preview-v1.2","team_identity":"pending","evaluation_status":"not_evaluated","files":[{"path":p.relative_to(OUT).as_posix(),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]}
(OUT/"artifact-lock.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
files.append(OUT/"artifact-lock.json")
DEST.mkdir(parents=True,exist_ok=True)
archive=DEST/"jitu-competition-v1.2-preview.zip"
with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
    for p in files:
        bundle.write(p,p.relative_to(OUT).as_posix())
record={"archive":archive.name,"bytes":archive.stat().st_size,"sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"files":len(files)}
(DEST/"competition-package.lock.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record))
