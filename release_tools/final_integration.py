"""AgentForge v4.4: read-only integration audit + explicit task DB backup.

Never sends outreach, edits CRM, or initializes missing databases.
"""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "direct_b2b.py", "lead_qualification.py", "proposal_quality_guard.py",
    "growth_operations.py", "lead_prioritization.py",
    "daily_operations.py", "conversion_analytics.py",
    "pages/10_Direct_B2B.py", "pages/11_Growth_Operations.py",
    "pages/12_Lead_Prioritization.py", "pages/13_Daily_Operations.py",
    "pages/14_Conversion_Analytics.py",
)
def readonly_status(path, required_table):
    path = Path(path)
    if not path.is_file():
        return {"ok": False, "issue": "database missing"}
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True, timeout=5)) as db:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            table = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (required_table,)).fetchone()
            count = db.execute(f'SELECT COUNT(*) FROM "{required_table}"').fetchone()[0] if table else None
        return {"ok": integrity == "ok" and table is not None, "integrity": integrity,
                "table_present": table is not None, "records": count}
    except (sqlite3.Error, OSError) as e:
        return {"ok": False, "issue": type(e).__name__}
def audit(root=ROOT):
    root=Path(root)
    files={name:(root/name).is_file() for name in MODULES}
    crm=readonly_status(root/"leads.sqlite3","b2b_v20_prospects")
    tasks=readonly_status(root/"operations.sqlite3","growth_tasks")
    return {"files":files,"crm":crm,"tasks":tasks,
            "ok":all(files.values()) and crm["ok"] and tasks["ok"],
            "notes":["Snapshot audit; no write operations or outbound messages.",
                     "No historical conversion rate is implied.",
                     "Task completion never qualifies a CRM prospect."]}
def _hash(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()
def backup_tasks(root=ROOT):
    root=Path(root)
    source=root/"operations.sqlite3"
    if not readonly_status(source,"growth_tasks")["ok"]:
        raise RuntimeError("Task database missing or unhealthy")
    folder=root/"backups"
    folder.mkdir(exist_ok=True)
    name="operations_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+str(os.getpid())+".sqlite3"
    target=folder/name
    try:
        with closing(sqlite3.connect(source.resolve().as_uri()+"?mode=ro",uri=True,timeout=10)) as src:
            with closing(sqlite3.connect(target,timeout=10)) as dest:
                src.backup(dest)
        if not readonly_status(target,"growth_tasks")["ok"]:
            raise RuntimeError("Backup failed validation")
        manifest={"filename":name,"sha256":_hash(target),"bytes":target.stat().st_size}
        target.with_suffix(".json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        return target
    except Exception:
        target.unlink(missing_ok=True)
        target.with_suffix(".json").unlink(missing_ok=True)
        raise
def verify_tasks(path):
    path=Path(path)
    manifest=json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if manifest.get("filename")!=path.name or manifest.get("sha256")!=_hash(path):
        raise ValueError("Checksum mismatch")
    if not readonly_status(path,"growth_tasks")["ok"]:
        raise ValueError("Database integrity check failed")
    return manifest
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=("audit","backup-tasks","verify-tasks"))
    parser.add_argument("path",nargs="?")
    args=parser.parse_args()
    try:
        if args.action=="audit":
            result=audit()
            print(json.dumps(result,indent=2))
            return 0 if result["ok"] else 1
        if args.action=="backup-tasks":
            print("Task backup:",backup_tasks())
            return 0
        if not args.path:
            parser.error("verify-tasks requires backup file path")
        print(json.dumps(verify_tasks(args.path),indent=2))
        return 0
    except (OSError,ValueError,RuntimeError,sqlite3.Error) as e:
        print("ERROR:",str(e),file=sys.stderr)
        return 1
if __name__=="__main__":
    raise SystemExit(main())
