.PHONY: check-firstlot-demo check-no-client-data-commit check-firstlot-weekend check-firstlot-merge-safety check-firstlot-merge-safety-fast firstlot-demo-run firstlot-merge-packet

check-firstlot-demo:
	python3 scripts/check_firstlot_demo.py

check-no-client-data-commit:
	python3 scripts/check_no_client_data_commit.py

check-firstlot-weekend: check-no-client-data-commit
	python3 -m pytest tests/unit/test_local_csv_cli.py tests/unit/test_client_csv_normalizer.py tests/unit/test_client_smoke_runner.py tests/unit/test_firstlot_demo_outputs.py tests/unit/test_failed_sku_workflow.py tests/unit/test_month_history_workflow.py tests/unit/test_run_comparison.py tests/unit/test_csv_validation.py tests/unit/test_close_packet.py tests/unit/test_no_client_data_commit_guard.py tests/unit/test_merge_safety_gate.py tests/unit/test_merge_readiness_packet.py tests/unit/test_firstlot_v1_readiness_checklist.py -q
	python3 scripts/check_firstlot_demo.py

check-firstlot-merge-safety:
	python3 scripts/check_firstlot_merge_safety.py

check-firstlot-merge-safety-fast:
	python3 scripts/check_firstlot_merge_safety.py --fast

firstlot-demo-run:
	python3 scripts/regenerate_firstlot_demo_artifacts.py --out /tmp/firstlot-demo-v1 --fixed-out /tmp/firstlot-demo-fixed
	@printf '\nFirstLot local demo packets are ready for review:\n'
	@printf '  v1 failed-queue packet: /tmp/firstlot-demo-v1\n'
	@printf '  v2 fixed-rerun packet: /tmp/firstlot-demo-fixed\n'
	@printf 'Start dashboard demo with: cd cogs-dashboard && npm start\n'
	@printf 'Open: http://localhost:3000/demo\n'

firstlot-merge-packet:
	mkdir -p /tmp/firstlot-merge-readiness
	python3 scripts/generate_firstlot_merge_packet.py --json-out /tmp/firstlot-merge-readiness/packet.json --md-out /tmp/firstlot-merge-readiness/packet.md
