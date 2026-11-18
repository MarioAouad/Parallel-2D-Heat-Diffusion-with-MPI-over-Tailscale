#!/usr/bin/env python3
"""Verify the real archived evidence without MPI, NumPy, or network access.

This does not produce measurements. It checks that existing published files
still match their manifest and that the six datasets are internally consistent.
An error raises an exception and returns a nonzero process status.
"""
from datetime import datetime
from pathlib import Path
import csv
import hashlib
import json
import math
import re

REPO = Path(__file__).resolve().parents[2]
EXPECTED_HOSTS = {
    "heat1-local": ("heat-1", "heat-1"),
    "heat2-local": ("heat-2", "heat-2"),
    "heat3-local": ("heat-3", "heat-3"),
    "heat1-heat2": ("heat-1", "heat-2"),
    "heat1-heat3": ("heat-1", "heat-3"),
    "heat2-heat3": ("heat-2", "heat-3"),
}
SIZES = [2**exponent for exponent in range(3, 25)]


def require(condition, message):
    # Use explicit exceptions, not assert: verification must still operate
    # when Python is invoked with -O, which removes assert statements.
    if not condition:
        raise ValueError(message)


def main():
    results = REPO / "part0" / "results"
    manifest = json.loads((results / "file-manifest.json").read_text(encoding="utf-8"))
    require(len(manifest) == 30, "Need 30 archived files")
    published_paths = set()
    for item in manifest:
        path = (REPO / item["file"]).resolve()
        require(path.is_relative_to(results.resolve()), "Manifest path escapes results")
        require(path not in published_paths, "Duplicate manifest entry")
        published_paths.add(path)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        require(digest == item["sha256"], f"Published hash mismatch: {path.name}")
        require(len(data) == item["bytes"], f"Byte count mismatch: {path.name}")
        if not item["public_copy_sanitized"]:
            require(digest == item["original_sha256"], "Original measurement/log hash differs")

    total_rows = 0
    found_cases = set()
    for csv_path in sorted((results / "2026-11-17").glob("*/*.csv")):
        with csv_path.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == 22, f"Need 22 sizes in {csv_path.name}")
        label = rows[0]["label"]
        require(label in EXPECTED_HOSTS and label not in found_cases, "Unexpected/duplicate case")
        found_cases.add(label)
        require([int(row["bytes"]) for row in rows] == SIZES, "Wrong size coverage/order")
        for row in rows:
            require(row["label"] == label, "Mixed labels in one CSV")
            require((row["host0"], row["host1"]) == EXPECTED_HOSTS[label], "Wrong endpoint hosts")
            require(3 <= int(row["iterations"]) <= 10000, "Unexpected repetition count")
            require(int(row["warmup"]) == 1, "Unexpected archived warm-up count")
            rtt, one = float(row["roundtrip_s"]), float(row["oneway_s"])
            throughput = float(row["effective_MiB_s"])
            require(all(math.isfinite(x) and x > 0 for x in [rtt, one, throughput]), "Invalid value")
            # Tolerance allows rounding of the 12-digit scientific CSV output.
            require(math.isclose(rtt / 2, one, rel_tol=3e-10), "Incorrect half-RTT")
            require(math.isclose(int(row["bytes"]) / 1048576 / one, throughput,
                                 rel_tol=3e-10), "Incorrect effective throughput")
        log = csv_path.with_suffix(".log").read_text(encoding="utf-8")
        require(re.findall(r"Testing (\d+) bytes:", log) == list(map(str, SIZES)), "Incomplete log")
        require("Finished successfully. CSV contains measured results." in log, "No success marker")
        meta = csv_path.with_suffix(".meta.txt").read_text(encoding="utf-8")
        require(f"case={label}\n" in meta and "profile=full\n" in meta, "Wrong metadata")
        transport = "self,vader" if label.endswith("-local") else "tcp,self"
        require(f"transport={transport}\n" in meta, "Wrong archived transport")
        stamps = []
        for when in ["before", "after"]:
            path = csv_path.with_suffix(f".route-{when}.txt")
            require(path.resolve() in published_paths, "Missing route from manifest")
            text = path.read_text(encoding="utf-8")
            require(f"case={label}\n" in text, "Wrong route case")
            stamp = re.search(r"^utc=(.+)$", text, re.M)
            require(stamp is not None, "Missing route UTC")
            stamps.append(datetime.fromisoformat(stamp.group(1).replace("Z", "+00:00")))
        require(stamps[1] >= stamps[0], "Route snapshot timestamp order is reversed")
        total_rows += len(rows)
        print(f"PASS {label}: 22 sizes, correct hosts/arithmetic, completed log, route files")
    require(found_cases == set(EXPECTED_HOSTS), "Missing cases")
    actual_files = {p.resolve() for p in (results / "2026-11-17").rglob("*") if p.is_file()}
    require(actual_files == published_paths, "Archive and manifest file lists differ")
    print(f"Verified {len(manifest)} files, {len(found_cases)} cases and {total_rows} measured rows.")
    print("This checks archived evidence; it does not rerun the VMs or prove route continuity.")


if __name__ == "__main__":
    main()
