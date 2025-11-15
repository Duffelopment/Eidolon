"""Heuristic scanning utilities."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from .. import schemas


@dataclass
class ScanFinding:
    name: str
    severity: str
    description: str
    category: str | None = None

    def to_schema(self) -> schemas.FindingBase:
        return schemas.FindingBase(
            name=self.name,
            severity=self.severity,
            description=self.description,
            category=self.category,
        )


def _detect_json(content: str) -> bool:
    try:
        json.loads(content)
        return True
    except Exception:
        return False


def analyze_file(file_bytes: bytes, filename: str) -> Tuple[schemas.ScanBase, List[schemas.FindingBase]]:
    size = len(file_bytes)
    md5 = hashlib.md5(file_bytes).hexdigest()
    sha1 = hashlib.sha1(file_bytes).hexdigest()
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    mime_type, _ = mimetypes.guess_type(filename)

    try:
        text_content = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text_content = ""

    findings: List[ScanFinding] = []
    score = 0

    patterns: Iterable[tuple[str, str, str, str]] = (
        (
            "Powershell Execution",
            r"powershell\s*-", "High",
            "The file references PowerShell command execution which is often abused by malware.",
        ),
        (
            "Encoded Payload",
            r"base64\.(?:b64decode|decodebytes)|frombase64",
            "Medium",
            "Embedded Base64 routines can be used to hide malicious payloads.",
        ),
        (
            "Networking Routines",
            r"(requests|get|post)\s*\(http",
            "Medium",
            "The file performs HTTP requests, indicating potential command & control behaviour.",
        ),
        (
            "Command Execution",
            r"os\.system|subprocess\.Popen|CreateProcess",
            "High",
            "Execution of arbitrary commands may indicate malware attempting to spawn processes.",
        ),
        (
            "Suspicious Windows API",
            r"CreateRemoteThread|VirtualAllocEx|WriteProcessMemory",
            "High",
            "Memory tampering Windows APIs are a hallmark of injection malware.",
        ),
        (
            "Archive of Scripts",
            r"<script|function\s+onload",
            "Low",
            "Embedded script logic detected. Verify the source of the script.",
        ),
    )

    for name, pattern, severity, description in patterns:
        if text_content and re.search(pattern, text_content, re.IGNORECASE):
            findings.append(
                ScanFinding(
                    name=name,
                    severity=severity,
                    description=description,
                    category="Behaviour",
                )
            )
            score += {"Low": 1, "Medium": 3, "High": 5}[severity]

    if file_bytes.startswith(b"MZ"):
        findings.append(
            ScanFinding(
                name="Portable Executable",
                severity="Medium",
                description="Windows executable header detected. Inspect with caution.",
                category="File Type",
            )
        )
        score += 3

    if text_content and _detect_json(text_content.strip()[:2048]):
        findings.append(
            ScanFinding(
                name="Structured Configuration",
                severity="Low",
                description="Looks like the file contains JSON content.",
                category="Metadata",
            )
        )
        score += 1

    if size > 10 * 1024 * 1024:
        findings.append(
            ScanFinding(
                name="Large Payload",
                severity="Low",
                description="The file is larger than 10MB which can hinder manual review.",
                category="Metadata",
            )
        )
        score += 1

    summary: str | None
    if score >= 12:
        summary = "High risk – multiple critical indicators were discovered."
    elif score >= 6:
        summary = "Moderate risk – investigate the highlighted behaviours."
    elif findings:
        summary = "Low risk – minor indicators present."
    else:
        summary = "No obvious issues detected."

    scan_schema = schemas.ScanBase(
        filename=filename,
        size=size,
        md5=md5,
        sha1=sha1,
        sha256=sha256,
        mime_type=mime_type,
        score=score,
        summary=summary,
    )
    finding_schemas = [finding.to_schema() for finding in findings]
    return scan_schema, finding_schemas


def build_graph_payload(scan: schemas.Scan, findings: List[schemas.Finding]) -> schemas.GraphResponse:
    nodes = [
        schemas.GraphNode(id=f"scan-{scan.id}", label=scan.filename, type="file"),
        schemas.GraphNode(id=f"md5-{scan.id}", label=f"MD5: {scan.md5}", type="hash"),
        schemas.GraphNode(id=f"sha1-{scan.id}", label=f"SHA1: {scan.sha1}", type="hash"),
        schemas.GraphNode(id=f"sha256-{scan.id}", label=f"SHA256: {scan.sha256}", type="hash"),
    ]
    links = [
        schemas.GraphLink(source=f"scan-{scan.id}", target=f"md5-{scan.id}", label="hash"),
        schemas.GraphLink(source=f"scan-{scan.id}", target=f"sha1-{scan.id}", label="hash"),
        schemas.GraphLink(source=f"scan-{scan.id}", target=f"sha256-{scan.id}", label="hash"),
    ]

    if scan.mime_type:
        nodes.append(
            schemas.GraphNode(
                id=f"mime-{scan.id}", label=f"MIME: {scan.mime_type}", type="metadata"
            )
        )
        links.append(
            schemas.GraphLink(
                source=f"scan-{scan.id}", target=f"mime-{scan.id}", label="mime"
            )
        )

    severity_order = {"Low": 0, "Medium": 1, "High": 2}
    sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.severity, 0), reverse=True)

    for finding in sorted_findings:
        finding_node_id = f"finding-{finding.id}"
        nodes.append(
            schemas.GraphNode(
                id=finding_node_id,
                label=f"{finding.severity}: {finding.name}",
                type="finding",
            )
        )
        links.append(
            schemas.GraphLink(
                source=f"scan-{scan.id}",
                target=finding_node_id,
                label=finding.category or "finding",
            )
        )

    return schemas.GraphResponse(nodes=nodes, links=links)
