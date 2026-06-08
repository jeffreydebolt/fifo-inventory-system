from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
READY_DOC = REPO_ROOT / "docs" / "plans" / "firstlot-v1-ready-to-try.md"
MAKEFILE = REPO_ROOT / "Makefile"


def test_firstlot_v1_ready_to_try_checklist_exists_and_tracks_required_surfaces():
    content = READY_DOC.read_text()

    required_phrases = [
        "Status: v1-ready for a local/demo try",
        "Local/demo FirstLot flow can run end-to-end",
        "CLI/docs tell Jeff exactly how to try it",
        "month-end COGS summary",
        "remaining layers",
        "audit/detail",
        "failed SKU/shortfall queue",
        "close packet",
        "Dashboard `/demo`",
        "Amazon mock boundary",
        "source queue",
        "day-zero basis/blockers",
        "inventory planning/replenishment",
        "run comparison/history",
        "Printing Press-style merge readiness process",
        "make check-firstlot-weekend",
        "make check-firstlot-merge-safety",
        "no `.env` reads",
        "no live Amazon",
        "no live DB",
        "no Storage Standard/client-data mutation",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in content]
    assert missing == []


def test_firstlot_v1_ready_to_try_checklist_points_to_safe_try_commands():
    content = READY_DOC.read_text()

    assert "make firstlot-demo-run" in content
    assert "python3.11 scripts/regenerate_firstlot_demo_artifacts.py" in content
    assert "--out /tmp/firstlot-demo-v1" in content
    assert "--fixed-out /tmp/firstlot-demo-fixed" in content
    assert "http://localhost:3000/demo" in content
    assert "npm test -- --runTestsByPath src/App.test.js --watchAll=false" in content
    assert "branch-only `make check-firstlot-merge-safety`" in content
    assert "fails closed there to prevent direct-main work" in content


def test_firstlot_demo_run_target_stays_available_for_reviewer_handoff():
    makefile = MAKEFILE.read_text()

    assert "firstlot-demo-run:" in makefile
    assert "PYTHON ?= $(shell command -v python3.11" in makefile
    assert "scripts/regenerate_firstlot_demo_artifacts.py --out /tmp/firstlot-demo-v1 --fixed-out /tmp/firstlot-demo-fixed" in makefile
    assert "FirstLot local demo packets are ready for review" in makefile
    assert "http://localhost:3000/demo" in makefile
