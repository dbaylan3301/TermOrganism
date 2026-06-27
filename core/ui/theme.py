"""Unified TermOrganism theme — consistent colors across all output."""

# Scalpbot-inspired dark palette
COLORS = {
    "primary": "#00D4AA",
    "secondary": "#7C3AED",
    "accent": "#F59E0B",
    "success": "#10B981",
    "danger": "#EF4444",
    "warning": "#F97316",
    "muted": "#6B7280",
    "text": "#F8FAFC",
    "border": "#334155",
    "info": "#38BDF8",
    "panel": "#7C3AED",
    "memory": "#F59E0B",
}

# Rich-compatible style strings
STYLE = {
    "primary": f"bold {COLORS['primary']}",
    "secondary": f"bold {COLORS['secondary']}",
    "accent": f"bold {COLORS['accent']}",
    "success": f"bold {COLORS['success']}",
    "danger": f"bold {COLORS['danger']}",
    "warning": f"bold {COLORS['warning']}",
    "muted": COLORS["muted"],
    "text": COLORS["text"],
    "border": COLORS["border"],
    "info": COLORS["info"],
    "panel": COLORS["panel"],
    "memory": COLORS["memory"],
    "dim": COLORS["muted"],
    "ok": COLORS["success"],
    "err": COLORS["danger"],
}

# Box style for panels
from rich import box
PANEL_BOX = box.ROUNDED
HEAVY_BOX = box.DOUBLE
