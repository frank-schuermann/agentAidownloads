"""
Generate KnownIssue, Runbook, and SOP text files derived from articles_en-us.json.

These files use the correct filename prefixes (KnownIssue_, Runbook_, SOP_) so that
generate_knowledge_graph.py can ingest them and create Knowledge Graph nodes/edges.

Usage:
    python generate_derived_docs.py
"""

import json
import os
import re
import textwrap
from html.parser import HTMLParser
from datetime import datetime


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def handle_entityref(self, name: str):
        from html import unescape
        self._parts.append(unescape(f"&{name};"))

    def handle_charref(self, name: str):
        from html import unescape
        self._parts.append(unescape(f"&#{name};"))

    def get_text(self) -> str:
        return "".join(self._parts)


def html_to_text(html: str) -> str:
    if not html:
        return ""
    extractor = HTMLTextExtractor()
    extractor.feed(html)
    text = extractor.get_text()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sanitize_filename(text: str, max_len: int = 80) -> str:
    text = re.sub(r"\s*-\s*Microsoft Support\s*$", "", text, flags=re.IGNORECASE)
    name = re.sub(r"[^\w\s-]", "", text)
    name = re.sub(r"[\s]+", "_", name.strip())
    if len(name) > max_len:
        name = name[:max_len].rstrip("_")
    return name


def wrap_text(text: str, width: int = 80) -> str:
    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
        elif len(paragraph) > width:
            lines.extend(textwrap.wrap(paragraph, width=width))
        else:
            lines.append(paragraph)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Article classification
# ---------------------------------------------------------------------------

# Patterns that indicate an article describes a known issue / error / bug
KNOWN_ISSUE_PATTERNS = [
    r"error|fail|crash|issue|bug|vulner|broken|cannot|unable|missing",
    r"blue\s?screen|bugcheck|0x[0-9a-fA-F]{4,}|BSOD",
    r"not\s+work|greyed?\s*out|stuck|hang|timeout|denied",
    r"prompted|unexpected|corrupt|leak|regression",
]
KNOWN_ISSUE_RE = re.compile("|".join(KNOWN_ISSUE_PATTERNS), re.IGNORECASE)

# Patterns that indicate a procedure/runbook/how-to
RUNBOOK_PATTERNS = [
    r"^how\s+to\b",
    r"^procedure[:\s]",
    r"\bstep[\s-]by[\s-]step\b",
    r"\btroubleshoot\b",
    r"make\s+exceptions?\b",
    r"\baudit\b.*\bhow\b|\bhow\b.*\baudit\b",
    r"\bretrieve\b.*\bthrough\s+powershell\b",
    r"\bin-place\s+upgrade\b",
    r"\bunderstanding\b",
    r"\boverview\b",
]
RUNBOOK_RE = re.compile("|".join(RUNBOOK_PATTERNS), re.IGNORECASE)

# Patterns for SOP (formal procedures, onboarding, policy)
SOP_PATTERNS = [
    r"^procedure[:\s].*visops|^procedure[:\s].*onboard",
    r"\bpolicy\b.*\bclarification\b",
    r"\bprocess[:\s].*setup\b",
    r"\barchived.*procedure\b",
]
SOP_RE = re.compile("|".join(SOP_PATTERNS), re.IGNORECASE)

# Skip patterns – generic updates, patches, release notes (these don't make good
# KnownIssue/Runbook/SOP documents)
SKIP_PATTERNS = [
    r"^(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d",
    r"^KB\d{7}",
    r"\bSafe\s+OS\s+Dynamic\s+Update\b",
    r"\bSetup\s+Dynamic\s+Update\b",
    r"\bCumulative\s+Update\b",
    r"\bMonthly\s+Rollup\b",
    r"\bSecurity[\s-]only\s+update\b",
    r"\bSecurity\s+update\s+for\b",
    r"\bSecurity\s+and\s+Quality\s+Rollup\b",
    r"\bHotpatch\b",
    r"\bOS\s+Build\b",
    r"^test\d*$|^testArticle$",
    r"\bReading\s+Coach\b",
    r"\bGaming\s+in\s+Microsoft\s+Teams\b",
    r"\bAccessibility\s+in\b",
    r"\bMinute\s+Fair\s+Usage\b",
    r"\bHow\s+to\s+buy\s+from\b",
    r"\bFile\s+upload\s+in\s+Microsoft\s+Copilot\b",
    r"\bManage\s+channel\s+notifications\b",
    r"\bCustomize\s+your\s+calendar\b",
    r"\bGet\s+started\s+with\b",
    r"\bProgress\s+over\s+time\b",
    r"MCI\s+Engagements",
    r"Word_Chat\s+QnA",
    r"\bUpdate\s+\d+\.\d+\s+for\s+Microsoft\s+Dynamics\b",
    r"\bSystem\s+requirements\s+for\b",
    r"\bInteroperable\s+Assistive\b",
    r"\bRestore\s+your\s+access\b",
    r"\bDynamic\s+list\s+filtering\b",
]
SKIP_RE = re.compile("|".join(SKIP_PATTERNS), re.IGNORECASE)


def classify_article(title: str, content_text: str) -> str | None:
    """Return 'KnownIssue', 'Runbook', 'SOP', or None (skip)."""
    if SKIP_RE.search(title):
        return None
    if SOP_RE.search(title):
        return "SOP"
    if RUNBOOK_RE.search(title):
        return "Runbook"
    if KNOWN_ISSUE_RE.search(title):
        return "KnownIssue"
    # Check content for issue indicators if title was ambiguous
    if KNOWN_ISSUE_RE.search(content_text[:500]):
        return "KnownIssue"
    return None


# ---------------------------------------------------------------------------
# Extract structured sections from raw article text
# ---------------------------------------------------------------------------

def extract_symptoms(text: str) -> str:
    """Try to find symptom/summary sections in the article text."""
    patterns = [
        r"(?:Summary|Symptom|Symptoms?)[:/\s]*(.{50,500}?)(?:\n\n|Details:|Cause|Resolution|Workaround|Root\s*Cause)",
        r"(?:Issue|Problem)[:/\s]*(.{50,400}?)(?:\n\n|Details:|Cause|Resolution)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    # Fallback: first ~300 chars
    return text[:300].strip()


def extract_cause(text: str) -> str:
    """Try to find root cause section."""
    patterns = [
        r"(?:Cause|Root\s*Cause)[:/\s]*(.{30,500}?)(?:\n\n|Resolution|Workaround|Fix|Article\s+resolution)",
        r"(?:Because of|Due to|This occurs when)[:/\s]*(.{30,400}?)(?:\n\n|Resolution|Workaround|Fix)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""


def extract_workaround(text: str) -> str:
    """Try to find workaround/resolution section."""
    patterns = [
        r"(?:Workaround|Resolution|Fix|Article\s+resolution|Mitigation)[:/\s]*(.{30,600})",
        r"(?:This\s+issue\s+is\s+addressed\s+in\s+\w+)(.{0,200})",
        r"(?:advised the customer to|recommended to|the fix is)[:/\s]*(.{30,400})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()[:600]
    return ""


def extract_steps(text: str) -> str:
    """Try to find step-by-step instructions from the article text."""
    # Look for numbered steps or bullet patterns
    step_pattern = r"(?:Step\s*\d|^\s*\d+[\.\)]\s+)"
    lines = text.split("\n")
    step_lines = []
    capturing = False
    for line in lines:
        if re.search(step_pattern, line, re.IGNORECASE):
            capturing = True
        if capturing:
            step_lines.append(line)
    if step_lines:
        return "\n".join(step_lines[:30])
    # Fallback: return the main content body
    return text[:800]


# ---------------------------------------------------------------------------
# Document templates
# ---------------------------------------------------------------------------

SEP = "=" * 80

def generate_known_issue(article: dict, content_text: str, ki_counter: int) -> str:
    title = article.get("title", "Untitled")
    article_id = article.get("articlepublicnumber", "N/A")
    created = article.get("createdon", "")[:10]
    modified = article.get("modifiedon", "")[:10]
    url = article.get("msdyn_ingestedarticleurl", "")
    ki_id = f"KI-{article_id}"

    symptoms = extract_symptoms(content_text)
    cause = extract_cause(content_text)
    workaround = extract_workaround(content_text)

    # Determine severity heuristic
    severity = "P3"
    if re.search(r"crash|BSOD|bugcheck|data\s*loss|security|vulner", content_text, re.IGNORECASE):
        severity = "P1"
    elif re.search(r"fail|error|unable|cannot|block", content_text, re.IGNORECASE):
        severity = "P2"

    # Determine status
    status = "Investigating"
    if workaround:
        status = "Workaround Available"
    if re.search(r"addressed in KB|fixed in|resolved", content_text, re.IGNORECASE):
        status = "Fix Available"

    # Detect affected product/service for tags
    tags = set()
    tag_map = {
        "Windows": r"\bWindows\b",
        "BitLocker": r"\bBitLocker\b",
        "ConfigMgr": r"\bConfigMgr|SCCM\b",
        "Active Directory": r"\bADDS|Active Directory|AD\b",
        "SharePoint": r"\bSharePoint\b",
        "RDS": r"\bRDS|Remote Desktop\b",
        "Kerberos": r"\bKerberos\b",
        "PKI": r"\bPKI|Certificate\b",
        "Wi-Fi": r"\bWi-?Fi\b",
        "Group Policy": r"\bGroup Policy|GPO|GPP\b",
        "WSL": r"\bWSL|wsl\.exe\b",
        "Hyper-V": r"\bHyper-V\b",
        "WSUS": r"\bWSUS\b",
        "Intune": r"\bIntune\b",
        "Cloud Witness": r"\bCloud Witness\b",
        "OneDrive": r"\bOneDrive\b",
        "SQL": r"\bSQL\b",
        "LSASS": r"\bLSASS\b",
        "Cluster": r"\bCluster|Failover\b",
    }
    for tag, pat in tag_map.items():
        if re.search(pat, title + " " + content_text[:500], re.IGNORECASE):
            tags.add(tag)

    lines = [
        SEP,
        f"KNOWN ISSUE — {ki_id}",
        title,
        SEP,
        "",
        f"Issue ID     : {ki_id}",
        f"Severity     : {severity}",
        f"Status       : {status}",
        f"Reported     : {created}",
        f"Last Updated : {modified}",
        f"Source KB     : {article_id}",
    ]
    if url:
        lines.append(f"Reference    : {url}")
    if tags:
        lines.append(f"Tags         : {', '.join(sorted(tags))}")

    lines += ["", "SYMPTOMS:", "---------"]
    lines.append(wrap_text(symptoms))

    if cause:
        lines += ["", "ROOT CAUSE:", "-----------"]
        lines.append(wrap_text(cause))

    lines += ["", "IMPACT:", "-------"]
    impact = f"Affects systems running the described configuration. See source KB {article_id} for full scope."
    lines.append(wrap_text(impact))

    if workaround:
        lines += ["", "WORKAROUND:", "-----------"]
        lines.append(wrap_text(workaround))
    else:
        lines += ["", "WORKAROUND:", "-----------"]
        lines.append("No workaround documented yet. Monitor source KB for updates.")

    lines += [
        "",
        "RELATED ARTICLES:",
        "-----------------",
        f"- KB Article: {article_id}",
        "",
        SEP,
    ]

    return "\n".join(lines) + "\n"


def generate_runbook(article: dict, content_text: str, rb_counter: int) -> str:
    title = article.get("title", "Untitled")
    article_id = article.get("articlepublicnumber", "N/A")
    modified = article.get("modifiedon", "")[:10]
    url = article.get("msdyn_ingestedarticleurl", "")
    rb_id = f"RB-{article_id}"

    steps = extract_steps(content_text)

    # Detect category
    category = "Operational Procedure"
    if re.search(r"troubleshoot|fix|resolv", title, re.IGNORECASE):
        category = "Troubleshooting"
    elif re.search(r"upgrade|install|setup|configure", title, re.IGNORECASE):
        category = "Configuration / Setup"
    elif re.search(r"audit|monitor|check", title, re.IGNORECASE):
        category = "Audit / Compliance"

    lines = [
        SEP,
        f"RUNBOOK — {rb_id}",
        title,
        SEP,
        "",
        f"Runbook ID        : {rb_id}",
        f"Category          : {category}",
        f"Estimated Time    : 30 minutes",
        f"Last Updated      : {modified}",
        f"Source KB          : {article_id}",
        f"Trigger           : Follow this runbook when encountering the scenario described below.",
    ]
    if url:
        lines.append(f"Reference         : {url}")

    lines += [
        "",
        SEP,
        "PRE-REQUISITES:",
        SEP,
        "- Administrative access to the affected system",
        "- Backup of current configuration before making changes",
        "- Relevant logs collected (Event Viewer, application logs)",
        "",
        SEP,
        "PROCEDURE:",
        SEP,
        "",
    ]

    lines.append(wrap_text(content_text[:2000]))

    lines += [
        "",
        SEP,
        "VALIDATION:",
        SEP,
        "1. Confirm the issue is resolved after applying the steps above.",
        "2. Monitor the system for 30 minutes for stability.",
        "3. If the issue persists, escalate per SOP-ESC-P1.",
        "",
        "RELATED ARTICLES:",
        "-----------------",
        f"- KB Article: {article_id}",
        "",
        SEP,
    ]

    return "\n".join(lines) + "\n"


def generate_sop(article: dict, content_text: str, sop_counter: int) -> str:
    title = article.get("title", "Untitled")
    article_id = article.get("articlepublicnumber", "N/A")
    modified = article.get("modifiedon", "")[:10]
    url = article.get("msdyn_ingestedarticleurl", "")
    sop_id = f"SOP-{article_id}"

    # Determine category
    category = "Operational Procedure"
    if re.search(r"onboard", title, re.IGNORECASE):
        category = "Onboarding"
    elif re.search(r"password|identity|MID", title, re.IGNORECASE):
        category = "Identity & Access Management"
    elif re.search(r"policy|compliance", title, re.IGNORECASE):
        category = "Policy & Compliance"

    lines = [
        SEP,
        f"STANDARD OPERATING PROCEDURE — {sop_id}",
        title,
        SEP,
        "",
        f"SOP ID            : {sop_id}",
        f"Category          : {category}",
        f"Effective Date    : {modified}",
        f"Last Reviewed     : {modified}",
        f"Source KB          : {article_id}",
        f"Applies To        : Support Engineers, IT Administrators",
    ]
    if url:
        lines.append(f"Reference         : {url}")

    lines += [
        "",
        SEP,
        "PURPOSE:",
        SEP,
        f"This SOP documents the standard procedure for: {title}",
        "",
        SEP,
        "PROCEDURE:",
        SEP,
        "",
    ]

    lines.append(wrap_text(content_text[:2000]))

    lines += [
        "",
        SEP,
        "COMPLETION CRITERIA:",
        SEP,
        "- All steps executed successfully",
        "- Changes documented in the ticket/change record",
        "- Stakeholders notified of completion",
        "",
        "RELATED ARTICLES:",
        "-----------------",
        f"- KB Article: {article_id}",
        "",
        SEP,
    ]

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "raw_data", "articles_en-us.json")
    output_dir = os.path.join(script_dir, "data")
    os.makedirs(output_dir, exist_ok=True)

    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    counters = {"KnownIssue": 0, "Runbook": 0, "SOP": 0}
    generated = []
    skipped = 0

    for article in articles:
        title = article.get("title", "")
        content_html = article.get("content", "")
        if not title or not content_html:
            skipped += 1
            continue

        content_text = html_to_text(content_html)
        doc_type = classify_article(title, content_text)

        if doc_type is None:
            skipped += 1
            continue

        article_id = article.get("articlepublicnumber", "UNKNOWN")
        base_name = sanitize_filename(title)
        counters[doc_type] += 1

        if doc_type == "KnownIssue":
            text = generate_known_issue(article, content_text, counters[doc_type])
            filename = f"KnownIssue_{article_id}_{base_name}.txt"
        elif doc_type == "Runbook":
            text = generate_runbook(article, content_text, counters[doc_type])
            filename = f"Runbook_{article_id}_{base_name}.txt"
        elif doc_type == "SOP":
            text = generate_sop(article, content_text, counters[doc_type])
            filename = f"SOP_{article_id}_{base_name}.txt"
        else:
            continue

        filepath = os.path.join(output_dir, filename)

        # Don't overwrite existing files
        if os.path.exists(filepath):
            print(f"  SKIP (exists): {filename}")
            skipped += 1
            continue

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

        generated.append((doc_type, filename))
        print(f"  {doc_type:12s} → {filename}")

    print(f"\n{'='*60}")
    print(f"Generated: {len(generated)} files")
    for dtype in ("KnownIssue", "Runbook", "SOP"):
        count = sum(1 for d, _ in generated if d == dtype)
        print(f"  {dtype:12s}: {count}")
    print(f"Skipped:   {skipped} articles (generic updates, no content, etc.)")
    print(f"Output:    {output_dir}")


if __name__ == "__main__":
    main()
