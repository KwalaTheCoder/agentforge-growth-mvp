"""Local-only AgentForge maintenance. Standard library only; no network operations."""
from __future__ import annotations
import argparse
from contextlib import closing
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_NAME = "leads.sqlite3"
BACKUP_DIR = "backups"
REQUIRED = ["AgentForge_Hub.py", "direct_b2b.py", "lead_qualification.py",
            "proposal_quality_guard.py", "pages/10_Direct_B2B.py"]
def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()
def check_db(dbpath):
    if not dbpath.is_file():
        return {"exists":False,"ok":False,"message":"Database not found"}
    try:
        # Read-only mode: no schema changes and no writes.
        uri=dbpath.resolve().as_uri()+"?mode=ro"
        with closing(sqlite3.connect(uri,uri=True,timeout=5)) as conn:
            row=conn.execute("PRAGMA integrity_check").fetchone()
            tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        ok=bool(row and row[0]=="ok")
        return {"exists":True,"ok":ok,"integrity":row[0] if row else "no result",
                "b2b_table": "b2b_v20_prospects" in tables}
    except (sqlite3.Error,OSError) as e:
        return {"exists":True,"ok":False,"message":str(e)}
def doctor(root=PROJECT_ROOT):
    root=Path(root)
    checks={name:(root/name).is_file() for name in REQUIRED}
    db=check_db(root/DB_NAME)
    return {"project_root":str(root),"files":checks,"database":db,
            "ok":all(checks.values()) and db["ok"] and db.get("b2b_table",False)}
def backup(root=PROJECT_ROOT):
    root=Path(root)
    source=root/DB_NAME
    if not source.is_file():
        raise FileNotFoundError(f"No database: {source}")
    target_dir=root/BACKUP_DIR
    target_dir.mkdir(exist_ok=True)
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target=target_dir/f"leads_{stamp}_{uuid.uuid4().hex[:10]}.sqlite3"
    # SQLite online backup safely includes committed WAL changes.
    source_uri=source.resolve().as_uri()+"?mode=ro"
    with closing(sqlite3.connect(source_uri,uri=True,timeout=20)) as src:
        with closing(sqlite3.connect(target)) as dest:
            src.backup(dest)
    status=check_db(target)
    if not status["ok"]:
        target.unlink(missing_ok=True)
        raise RuntimeError(f"Backup failed integrity check: {status}")
    manifest={"created_utc":stamp,"filename":target.name,"sha256":sha256(target),
              "bytes":target.stat().st_size}
    target.with_suffix(".json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return target
def verify_backup(path):
    path=Path(path)
    manifest_path=path.with_suffix(".json")
    if not manifest_path.is_file():
        raise ValueError("Missing backup manifest (.json)")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("filename")!=path.name or manifest.get("sha256")!=sha256(path):
        raise ValueError("Backup checksum mismatch")
    status=check_db(path)
    if not status["ok"]:
        raise ValueError(f"Backup corrupt: {status}")
    return manifest
def restore(root, backup_file, confirm=False):
    """Manual, offline restore; requires stopped app and explicit confirmation."""
    if not confirm:
        raise ValueError("Restore requires --confirm and a stopped Streamlit app.")
    root=Path(root)
    source=Path(backup_file).resolve()
    if source.parent!=(root/BACKUP_DIR).resolve():
        raise ValueError("Restore source must be in this project's backups directory.")
    verify_backup(source)
    db=root/DB_NAME
    # Refuse restore if WAL/SHM sidecars exist: app might still be running.
    if (root/(DB_NAME+"-wal")).exists() or (root/(DB_NAME+"-shm")).exists():
        raise RuntimeError("SQLite WAL/SHM files present. Stop the app and resolve them first.")
    if db.exists():
        safety=backup(root)
        print(f"Safety backup of current DB: {safety}")
    temp=root/(DB_NAME+".restore_tmp")
    try:
        shutil.copy2(source,temp)
        if not check_db(temp)["ok"]:
            raise RuntimeError("Restored temporary database failed integrity check.")
        os.replace(temp,db)
    finally:
        temp.unlink(missing_ok=True)
    return db
def main():
    parser=argparse.ArgumentParser(description="AgentForge local release maintenance")
    parser.add_argument("command",choices=["doctor","backup","verify","restore"])
    parser.add_argument("path",nargs="?",help="Backup file for verify/restore")
    parser.add_argument("--confirm",action="store_true",help="Explicit confirmation for restore")
    args=parser.parse_args()
    try:
        if args.command=="doctor":
            report=doctor()
            print(json.dumps(report,indent=2,ensure_ascii=False))
            return 0 if report["ok"] else 1
        if args.command=="backup":
            print("Backup:",backup())
            return 0
        if not args.path:
            parser.error("verify/restore requires a backup path")
        if args.command=="verify":
            print(json.dumps(verify_backup(args.path),indent=2))
        elif args.command=="restore":
            print("Restored:",restore(PROJECT_ROOT,args.path,args.confirm))
        return 0
    except (OSError,ValueError,RuntimeError,sqlite3.Error) as e:
        print(f"ERROR: {e}",file=sys.stderr)
        return 1
if __name__=="__main__":
    raise SystemExit(main())
