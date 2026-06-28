"""Integration tests for enhanced REPL features."""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_repo_summary():
    """Test repo summary command."""
    from core.commands.enhanced import get_repo_summary
    result = get_repo_summary()
    assert isinstance(result, str)
    assert "İstatistikler" in result


def test_repo_status():
    """Test repo status command."""
    from core.commands.enhanced import get_repo_status
    result = get_repo_status()
    assert isinstance(result, str)
    assert "Branch" in result


def test_project_detection():
    """Test project type detection."""
    from core.integrations.openstock import detect_project_type
    # Test in TermOrganism directory (Python project)
    result = detect_project_type(str(Path(__file__).parent.parent))
    assert result == "python"


def test_code_quality_analysis():
    """Test code quality analysis."""
    from core.repair.auto_fix import analyze_code_quality
    result = analyze_code_quality(str(Path(__file__).parent.parent / "core" / "ui" / "repl.py"))
    assert "lines" in result
    assert "functions" in result


def test_security_scan():
    """Test security scanning."""
    from core.analysis.security import scan_file_security
    issues = scan_file_security(str(Path(__file__).parent.parent / "core" / "ui" / "repl.py"))
    assert isinstance(issues, list)


def test_dependency_analysis():
    """Test dependency analysis."""
    from core.analysis.dependencies import analyze_python_deps
    result = analyze_python_deps(str(Path(__file__).parent.parent))
    assert "requirements" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
