.PHONY: check-firstlot-demo check-no-client-data-commit check-firstlot-weekend check-firstlot-merge-safety check-firstlot-merge-safety-fast firstlot-merge-packet

check-firstlot-demo:
	python3 scripts/check_firstlot_demo.py

check-no-client-data-commit:
	python3 scripts/check_no_client_data_commit.py

check-firstlot-weekend: check-no-client-data-commit
	python3 -m pytest tests/unit/test_local_csv_cli.py tests/unit/test_client_csv_normalizer.py tests/unit/test_client_smoke_runner.py tests/unit/test_firstlot_demo_outputs.py tests/unit/test_failed_sku_workflow.py tests/unit/test_month_history_workflow.py tests/unit/test_run_comparison.py tests/unit/test_csv_validation.py tests/unit/test_close_packet.py tests/unit/test_no_client_data_commit_guard.py tests/unit/test_merge_safety_gate.py tests/unit/test_merge_readiness_packet.py -q
	python3 scripts/check_firstlot_demo.py

check-firstlot-merge-safety:
	python3 scripts/check_firstlot_merge_safety.py

check-firstlot-merge-safety-fast:
	python3 scripts/check_firstlot_merge_safety.py --fast

firstlot-merge-packet:
	mkdir -p /tmp/firstlot-merge-readiness
	python3 scripts/generate_firstlot_merge_packet.py --json-out /tmp/firstlot-merge-readiness/packet.json --md-out /tmp/firstlot-merge-readiness/packet.md
