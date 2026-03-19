"""
Organize data/*.txt files into thematic subdirectories.

Structure:
  data/
    00_base_ccaas/          - Original hand-crafted CCaaS demo files
    01_windows_client/      - Windows Client & Desktop issues
    02_windows_server/      - Windows Server issues
    03_active_directory/    - AD, PKI, Kerberos, Group Policy
    04_configmgr/           - Configuration Manager / SCCM / WSUS
    05_sql_sharepoint/      - SQL Server, SharePoint, data services
    06_networking_security/ - Networking, Wi-Fi, Firewall, VBS, Security
    07_intune_misc/         - Intune, misc procedures and SOPs
    08_kb_raw/              - Raw KB article exports (not parsed by generator)

Usage:
    python organize_data.py          # move files
    python organize_data.py --undo   # move everything back to data/
"""

import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"

# ---------------------------------------------------------------------------
# Mapping: filename pattern -> target subfolder
# ---------------------------------------------------------------------------

# 00 - Original CCaaS base files (no KISP in the name)
BASE_FILES = {
    "FAQ_QM_Drift.txt",
    "KnownIssue_CopilotDelay.txt",
    "KnownIssue_QM_ScorecardDrift.txt",
    "KnownIssue_SafariChat.txt",
    "KnownIssue_VoiceTransferDrop.txt",
    "KnownIssue_WFM_ScheduleMismatch.txt",
    "ReleaseNotes_2025W1.txt",
    "ReleaseNotes_2025W2.txt",
    "ReleaseNotes_2025W2_QM.txt",
    "ReleaseNotes_2025W2_WFM.txt",
    "Runbook_QM_RubricCacheReset.txt",
    "Runbook_RoutingFix.txt",
    "Runbook_VoiceOutage.txt",
    "Runbook_WFM_ForecastRegen.txt",
    "SOP_P1_Escalation.txt",
    "SOP_QM_P2_SupervisorComms.txt",
    "SPO_CCaaS_Digital.txt",
    "SPO_CCaaS_Enterprise.txt",
    "UserGuide_AgentDesktop.txt",
    "UserGuide_QM_Admin.txt",
    "UserGuide_RoutingAdmin.txt",
    "UserGuide_Supervisor.txt",
    "UserGuide_WFM_Admin.txt",
}

# Generated KnownIssue/Runbook/SOP files mapped to services
# Key: substring in filename -> folder
WINDOWS_CLIENT_PATTERNS = [
    "KISP-034154",  # BitLocker recovery
    "KISP-029768",  # Apps missing icon
    "KISP-038696",  # Unknown Hard Error
    "KISP-035952",  # wsl.exe Access denied
    "KISP-042455",  # Add device greyed out
    "KISP-045125",  # Diagnostic Policy Service fails
    "KISP-052887",  # Search not working OneDrive
    "KISP-065986",  # Feature Update failed
    "KISP-163138",  # StoreWorker fails
    "KISP-026023",  # HAM overview (Runbook)
    "KISP-056707",  # GPO BLOCK UNTRUSTED FONTS (Runbook)
    "KISP-039440",  # Phone Link greyed out (KB)
    "KISP-053414",  # atbroker.exe (KB)
]

WINDOWS_SERVER_PATTERNS = [
    "KISP-039855",  # Bugcheck 0x9F
    "KISP-045141",  # RDS credentials fail
    "KISP-036662",  # Event ID 2017
    "KISP-167038",  # Server 2025 input lag
    "KISP-167166",  # Upgrade fails Read-Only
    "KISP-066859",  # Cloud Witness error
    "KISP-158818",  # SS cache timer expired
    "KISP-036746",  # Unsupported devices (Runbook)
    "KISP-037492",  # Language packs WSUS (Runbook)
    "KISP-057863",  # In-place upgrade (Runbook)
    "KISP-058929",  # Windows Continuous Delivery (Runbook)
]

AD_PATTERNS = [
    "KISP-033676",  # PKI Certificate Revocation
    "KISP-043824",  # PKI CA certificate error
    "KISP-041663",  # W32time sync fails
    "KISP-055437",  # LSASS crash Kerberos
    "KISP-057720",  # Klist.exe fails
    "KISP-154265",  # PasswordLastSet format
    "KISP-164087",  # Slow logon GPP
    "KISP-165805",  # SACL audit (Runbook)
    "KISP-040904",  # GPO versionNumber (Runbook)
    "KISP-062429",  # Security policy (KB)
]

CONFIGMGR_PATTERNS = [
    "KISP-035195",  # WINHTTP error
    "KISP-035939",  # SQL ODBC install
    "KISP-035982",  # Report export error
    "KISP-036294",  # Management Point DB
    "KISP-041643",  # Setup fails CertRegistry
    "KISP-046276",  # Client registration
    "KISP-046389",  # Cloud Management Gateway
    "KISP-048131",  # Error 80041313
    "KISP-048693",  # WSUS scan fails
    "KISP-062239",  # Client Health vcredist
]

SQL_SHAREPOINT_PATTERNS = [
    "KISP-040997",  # SQL role priority
    "KISP-042769",  # Remote Perfmon
    "KISP-118668",  # VAMT SQL connection
    "KISP-030430",  # SharePoint certificate
    "KISP-044920",  # SharePoint security update (KB)
]

NETWORKING_SECURITY_PATTERNS = [
    "KISP-029184",  # Error 1783 services/firewall
    "KISP-038306",  # Wi-Fi GP update
    "KISP-035578",  # WMI SecurityCenter2
    "KISP-033157",  # VBS Secure Kernel
    "KISP-027772",  # Driver Verifier ECP
    "KISP-043757",  # OpenSSH SYSLOG (KB)
    "KISP-037981",  # Citrix mmhook.dll (KB)
]

INTUNE_MISC_PATTERNS = [
    "KISP-156334",  # Intune app version (Runbook)
    "KISP-133594",  # Troubleshoot MSN (Runbook)
    "KISP-036107",  # Skype blocked accounts (SOP)
    "KISP-042484",  # VISOps Onboarding (SOP)
    "KISP-042558",  # VISOps Teams MID (SOP)
    "KISP-052820",  # XIA Mailbox Setup (SOP)
    "KISP-111464",  # VISOps Profiler (KB)
    "KISP-043874",  # SHA distribution lists (KB)
]


def determine_folder(filename: str) -> str:
    """Determine the target subfolder for a file."""
    if filename in BASE_FILES:
        return "00_base_ccaas"

    for pat in WINDOWS_CLIENT_PATTERNS:
        if pat in filename:
            return "01_windows_client"
    for pat in WINDOWS_SERVER_PATTERNS:
        if pat in filename:
            return "02_windows_server"
    for pat in AD_PATTERNS:
        if pat in filename:
            return "03_active_directory"
    for pat in CONFIGMGR_PATTERNS:
        if pat in filename:
            return "04_configmgr"
    for pat in SQL_SHAREPOINT_PATTERNS:
        if pat in filename:
            return "05_sql_sharepoint"
    for pat in NETWORKING_SECURITY_PATTERNS:
        if pat in filename:
            return "06_networking_security"
    for pat in INTUNE_MISC_PATTERNS:
        if pat in filename:
            return "07_intune_misc"

    # Remaining KB_ files go to raw
    if filename.startswith("KB_"):
        return "08_kb_raw"

    # Fallback
    return "08_kb_raw"


def organize():
    """Move files into thematic subdirectories."""
    # Only work with files directly in data/
    files = [f for f in DATA_DIR.iterdir() if f.is_file() and f.suffix == ".txt"]

    if not files:
        print("No .txt files found directly in data/. Already organized?")
        return

    moved = {}
    for f in sorted(files):
        folder = determine_folder(f.name)
        target_dir = DATA_DIR / folder
        target_dir.mkdir(exist_ok=True)
        target = target_dir / f.name
        shutil.move(str(f), str(target))
        moved.setdefault(folder, []).append(f.name)

    print("Files organized:\n")
    for folder in sorted(moved):
        print(f"  {folder}/ ({len(moved[folder])} files)")
        for name in moved[folder][:5]:
            print(f"    - {name}")
        if len(moved[folder]) > 5:
            print(f"    ... and {len(moved[folder]) - 5} more")
        print()

    total = sum(len(v) for v in moved.values())
    print(f"Total: {total} files moved into {len(moved)} folders.")


def undo():
    """Move all files from subdirectories back to data/."""
    count = 0
    for subdir in sorted(DATA_DIR.iterdir()):
        if subdir.is_dir():
            for f in subdir.iterdir():
                if f.is_file() and f.suffix == ".txt":
                    shutil.move(str(f), str(DATA_DIR / f.name))
                    count += 1
            # Remove empty dir
            if not any(subdir.iterdir()):
                subdir.rmdir()

    print(f"Undo complete: {count} files moved back to data/.")


if __name__ == "__main__":
    if "--undo" in sys.argv:
        undo()
    else:
        organize()
