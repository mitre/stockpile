
#!/usr/bin/env python3
import argparse
import csv
import os
import sys
import uuid
import json
from typing import Dict, Any, List, Tuple

try:
    import yaml  # PyYAML
except ImportError:
    print("This script requires PyYAML. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REQUIRED_COLUMNS = [
    "id","name","description","tactic",
    "technique_attack_id","technique_full_name",
    "windows_command","windows_executor",
    "linux_command","linux_executor",
    "darwin_command","darwin_executor",
    "privilege","payloads","cleanup",
    "target_dir","yml_filename"
]

def row_to_ability(row: Dict[str,str]) -> Dict[str, Any]:
    # Top-level fields
    ability: Dict[str, Any] = {
        "id": row.get("id") if row.get("id") and row.get("id") != "<GENERATE_UUIDv4>" else str(uuid.uuid4()),
        "name": (row.get("name") or "").strip(),
        "description": (row.get("description") or "").strip(),
        "tactic": (row.get("tactic") or "").strip().lower(),
        "technique": {
            "attack_id": (row.get("technique_attack_id") or "").strip(),
            "name": (row.get("technique_full_name") or "").strip(),
        },
        "platforms": {}
    }

    # Optional fields
    privilege = (row.get("privilege") or "").strip()
    if privilege:
        ability["privilege"] = privilege

    payloads = [p.strip() for p in (row.get("payloads") or "").split(",") if p.strip()]
    if payloads:
        ability["payloads"] = payloads

    # Build per-platform blocks
    def add_platform_block(platform_key: str, executor_key: str, command: str, cleanup_cmd: str):
        if not command:
            return
        platform_key = platform_key.lower()
        if platform_key not in ("windows","linux","darwin"):
            return
        # Default sensible executors
        if not executor_key:
            executor_key = "psh" if platform_key == "windows" else "sh"
        if platform_key not in ability["platforms"]:
            ability["platforms"][platform_key] = {}
        ability["platforms"][platform_key][executor_key] = {"command": command}
        if cleanup_cmd:
            ability["platforms"][platform_key][executor_key]["cleanup"] = cleanup_cmd

    cleanup = (row.get("cleanup") or "").strip()
    add_platform_block("windows", row.get("windows_executor","").strip(), (row.get("windows_command") or "").strip(), cleanup)
    add_platform_block("linux", row.get("linux_executor","").strip(), (row.get("linux_command") or "").strip(), cleanup)
    add_platform_block("darwin", row.get("darwin_executor","").strip(), (row.get("darwin_command") or "").strip(), cleanup)

    return ability

def write_yaml_file(ability: Dict[str,Any], out_path: str):
    # Stockpile abilities are typically a YAML list with a single item
    content = [ability]
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(content, f, sort_keys=False, allow_unicode=True)

def main():
    ap = argparse.ArgumentParser(description="Build Caldera Stockpile ability YAMLs from a CSV.")
    ap.add_argument("csv_path", help="Path to builder CSV (e.g., caldera_gap_for_yaml_builder_with_vars.csv)")
    ap.add_argument("--out-root", default=".", help="Root directory to write abilities under (default: current directory)")
    ap.add_argument("--dry-run", action="store_true", help="Parse and validate only; do not write files")
    args = ap.parse_args()

    if not os.path.isfile(args.csv_path):
        print(f"ERROR: CSV not found: {args.csv_path}", file=sys.stderr)
        sys.exit(2)

    written: List[str] = []
    skipped: List[Tuple[int,str]] = []

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing_cols:
            print(f"ERROR: CSV is missing required columns: {missing_cols}", file=sys.stderr)
            sys.exit(3)

        for idx, row in enumerate(reader, start=2):  # 1-based header, so data starts at line 2
            # Validate essentials
            tech_id = (row.get("technique_attack_id") or "").strip()
            name = (row.get("name") or "").strip()
            tactic = (row.get("tactic") or "").strip().lower()
            yml_filename = (row.get("yml_filename") or "").strip()
            target_dir = (row.get("target_dir") or "").strip()

            if not tech_id or not name or not tactic:
                skipped.append((idx, f"Missing one of required fields (technique_attack_id/name/tactic)."))
                continue

            ability = row_to_ability(row)

            # If no platform commands exist, skip
            if not ability["platforms"]:
                skipped.append((idx, "No platform commands provided; nothing to write."))
                continue

            # Decide output path
            # If CSV provides target_dir/yml_filename, prefer those
            out_dir = os.path.join(args.out_root, target_dir) if target_dir else args.out_root
            if not yml_filename:
                # Fallback filename from technique id + slug name
                def slugify(s: str) -> str:
                    import re
                    s = s.lower()
                    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
                    return s[:80]
                yml_filename = f"{tech_id}__{slugify(name)}.yml"
            out_path = os.path.join(out_dir, yml_filename)

            if not args.dry_run:
                os.makedirs(out_dir, exist_ok=True)
                write_yaml_file(ability, out_path)
                written.append(out_path)

    # Summary
    print(f"Wrote {len(written)} ability file(s).")
    for p in written[:10]:
        print(f"  - {p}")
    if len(written) > 10:
        print(f"  ... (+{len(written)-10} more)")
    if skipped:
        print(f"Skipped {len(skipped)} row(s):", file=sys.stderr)
        for line_no, reason in skipped[:10]:
            print(f"  line {line_no}: {reason}", file=sys.stderr)
        if len(skipped) > 10:
            print(f"  ... (+{len(skipped)-10} more)", file=sys.stderr)

if __name__ == "__main__":
    main()
