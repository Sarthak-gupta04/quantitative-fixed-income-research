"""Descriptive U.S. Treasury curve research, independent of portfolio rules.

The official Treasury daily par-yield feed is used because it exposes the
same 2-, 5-, and 10-year constant-maturity tenors as FRED DGS2/DGS5/DGS10
without requiring an API key. Yields and all derived values are percentage
points; missing tenor observations are never interpolated.
"""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from xml.etree import ElementTree as ET

import pandas as pd

SOURCE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
FIELDS = {"BC_2YEAR": "two_year", "BC_5YEAR": "five_year", "BC_10YEAR": "ten_year"}
DATA_NS = "http://schemas.microsoft.com/ado/2007/08/dataservices"
ATOM_NS = "http://www.w3.org/2005/Atom"
META_NS = "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"


def parse_treasury_xml(content: bytes) -> pd.DataFrame:
    """Read actual published observations; leave absent/blank tenors as NA."""
    root = ET.fromstring(content)
    rows = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        props = entry.find(f"{{{ATOM_NS}}}content/{{{META_NS}}}properties")
        if props is None:
            continue
        date_node = props.find(f"{{{DATA_NS}}}NEW_DATE")
        if date_node is None or not date_node.text:
            continue
        row = {"date": pd.Timestamp(date_node.text).normalize()}
        for source, target in FIELDS.items():
            node = props.find(f"{{{DATA_NS}}}{source}")
            row[target] = float(node.text) if node is not None and node.text else float("nan")
        rows.append(row)
    if not rows:
        raise ValueError("Treasury feed contained no dated yield observations")
    result = pd.DataFrame(rows).set_index("date").sort_index()
    if not result.index.is_unique:
        raise ValueError("Treasury feed contains duplicate dates")
    return result


def load_treasury_history(raw_dir: Path, start_year: int, end_year: int) -> tuple[pd.DataFrame, list[dict]]:
    """Cache yearly official XML with a hash and retrieval time per source file."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    def one_year(year: int) -> tuple[int, pd.DataFrame, dict]:
        url = f"{SOURCE}?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
        path = raw_dir / f"treasury_curve_{year}.xml"
        if path.exists():
            content = path.read_bytes()
            retrieval = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        else:
            with urlopen(url, timeout=45) as response:
                content = response.read()
            # Validate before caching a response such as an HTML error page.
            parse_treasury_xml(content)
            path.write_bytes(content)
            retrieval = datetime.now(timezone.utc).isoformat()
        frame = parse_treasury_xml(content)
        source = {
            "year": year, "url": url, "retrieved_at_utc": retrieval,
            "sha256": hashlib.sha256(content).hexdigest(),
            "rows": len(frame), "first_date": frame.index.min().date().isoformat(),
            "last_date": frame.index.max().date().isoformat(),
            "local_file": str(path.relative_to(raw_dir.parents[2])),
        }
        return year, frame, source

    # Yearly official feeds are independent. Bounded concurrency limits total
    # retrieval time without changing chronological output or data semantics.
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = sorted(pool.map(one_year, range(start_year, end_year + 1)), key=lambda item: item[0])
    return pd.concat([frame for _, frame, _ in results]).sort_index(), [source for _, _, source in results]


def calculate_curve(yields: pd.DataFrame) -> pd.DataFrame:
    """2s10s=10Y−2Y; 5s10s=10Y−5Y; butterfly=2×5Y−2Y−10Y."""
    required = {"two_year", "five_year", "ten_year"}
    if not required.issubset(yields.columns):
        raise ValueError(f"Missing Treasury tenor columns: {required - set(yields.columns)}")
    clean = yields.sort_index().dropna(subset=list(required)).copy()
    clean["level"] = clean["ten_year"]
    clean["slope_2s10s"] = clean["ten_year"] - clean["two_year"]
    clean["slope_5s10s"] = clean["ten_year"] - clean["five_year"]
    clean["curvature"] = 2 * clean["five_year"] - clean["two_year"] - clean["ten_year"]
    for field in ("level", "slope_2s10s", "slope_5s10s", "curvature"):
        clean[f"change_{field}"] = clean[field].diff()
    return clean


def align_curve_and_allocation(curve: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    """Exact-date intersection only: no forward-filling or inferred prices."""
    common = curve.index.intersection(weights.index)
    joined = curve.loc[common, ["level", "slope_2s10s", "curvature"]].join(
        weights.loc[common, ["SHY", "IEF", "TLT"]]
    )
    # The final jointly observed trading day of each calendar month.
    return joined.groupby(joined.index.to_period("M")).tail(1)
