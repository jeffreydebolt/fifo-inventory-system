PYTHON ?= $(shell command -v python3.11 2>/dev/null || command -v python3)

.PHONY: check-firstlot-demo check-no-client-data-commit check-firstlot-weekend check-firstlot-merge-safety check-firstlot-merge-safety-fast firstlot-demo-run firstlot-merge-packet

check-firstlot-demo:
	$(PYTHON) scripts/check_firstlot_demo.py

check-no-client-data-commit:
	$(PYTHON) scripts/check_no_client_data_commit.py

check-firstlot-weekend: check-no-client-data-commit
	$(PYTHON) -m pytest tests/unit/test_local_csv_cli.py tests/unit/test_client_csv_normalizer.py tests/unit/test_client_smoke_runner.py tests/unit/test_firstlot_demo_outputs.py tests/unit/test_failed_sku_workflow.py tests/unit/test_month_history_workflow.py tests/unit/test_run_comparison.py tests/unit/test_csv_validation.py tests/unit/test_close_packet.py tests/unit/test_no_client_data_commit_guard.py tests/unit/test_merge_safety_gate.py tests/unit/test_merge_readiness_packet.py tests/unit/test_firstlot_v1_readiness_checklist.py -q
	$(PYTHON) scripts/check_firstlot_demo.py

check-firstlot-merge-safety:
	$(PYTHON) scripts/check_firstlot_merge_safety.py

check-firstlot-merge-safety-fast:
	$(PYTHON) scripts/check_firstlot_merge_safety.py --fast

firstlot-demo-run:
	$(PYTHON) scripts/regenerate_firstlot_demo_artifacts.py --out /tmp/firstlot-demo-v1 --fixed-out /tmp/firstlot-demo-fixed
	@printf '\nFirstLot local demo packets are ready for review:\n'
	@printf '  v1 failed-queue packet: /tmp/firstlot-demo-v1\n'
	@printf '  v2 fixed-rerun packet: /tmp/firstlot-demo-fixed\n'
	@printf 'Start dashboard demo with: cd cogs-dashboard && npm start\n'
	@printf 'Open: http://localhost:3000/demo\n'

firstlot-merge-packet:
	mkdir -p /tmp/firstlot-merge-readiness
	$(PYTHON) scripts/generate_firstlot_merge_packet.py --json-out /tmp/firstlot-merge-readiness/packet.json --md-out /tmp/firstlot-merge-readiness/packet.md
