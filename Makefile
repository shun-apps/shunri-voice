PYTHON ?= python3

.PHONY: setup voices voice reference shunri gemini-voice-candidates gemini-voice-younger-candidates gemini-voice-speed-compare install-cli uninstall-cli worker-once install-reel-worker uninstall-reel-worker worker-status reel-renderer-setup remotion-renderer-setup remotion-poc motion-bank import-motion-bank reel reel-poc reel-poc-lipsync quicktime-copy self-check clean

setup:
	bash scripts/bootstrap.sh

voices:
	$(PYTHON) scripts/generate.py --text-file samples/reel_script.txt --preset all

voice:
	$(PYTHON) scripts/generate.py --text-file samples/reel_script.txt --preset default

reference:
	@test -n "$(FILE)" || (echo '使い方: make reference FILE="/path/to/sample.mp4"' && exit 1)
	$(PYTHON) scripts/import_reference.py "$(FILE)"

shunri:
	@test -f references/shunri.wav || (echo 'references/shunri.wav がありません。先に make reference FILE="..." を実行してください。' && exit 1)
	$(PYTHON) scripts/generate.py --text-file samples/reel_script.txt --preset clone --reference references/shunri.wav

gemini-voice-candidates:
	$(PYTHON) scripts/gemini_voice_candidates.py

gemini-voice-younger-candidates:
	$(PYTHON) scripts/gemini_voice_candidates.py --config config/gemini_voice_younger_candidates.json --output-dir outputs/gemini-voice-younger-candidates

gemini-voice-speed-compare:
	$(PYTHON) scripts/voice_speed_compare.py

install-cli:
	bash scripts/install_cli.sh

uninstall-cli:
	rm -f "$(HOME)/.local/bin/shunri"

worker-once:
	$(PYTHON) scripts/process_reel_jobs.py

install-reel-worker:
	bash scripts/install_reel_worker.sh

uninstall-reel-worker:
	bash scripts/uninstall_reel_worker.sh

worker-status:
	bash scripts/reel_worker_status.sh

reel-renderer-setup:
	docker build -t shunri-reel-renderer:local docker/reel-renderer

remotion-renderer-setup:
	docker build -f docker/remotion-renderer/Dockerfile -t shunri-remotion-renderer:local .

remotion-poc:
	$(PYTHON) scripts/render_remotion.py $(if $(WORK),--work-dir "$(WORK)",) $(if $(AUDIO),--audio "$(AUDIO)",) $(if $(OUTPUT),--output "$(OUTPUT)",)

motion-bank:
	$(PYTHON) scripts/prepare_motion_bank.py

import-motion-bank:
	@test -n "$(DIR)" || (echo '使い方: make import-motion-bank DIR="/path/to/clips"' && exit 1)
	$(PYTHON) scripts/import_motion_bank.py "$(DIR)"

reel:
	@test -n "$(FILE)" || (echo '使い方: make reel FILE="/path/to/script.txt"' && exit 1)
	$(PYTHON) scripts/reel_poc.py --file "$(FILE)"

reel-poc:
	@test -n "$(FILE)" || (echo '使い方: make reel-poc FILE="/path/to/script.txt"' && exit 1)
	$(PYTHON) scripts/reel_poc.py --file "$(FILE)"

reel-poc-lipsync:
	@test -n "$(FILE)" || (echo '使い方: make reel-poc-lipsync FILE="/path/to/script.txt"' && exit 1)
	@test -n "$SHUNRI_LIPSYNC_COMMAND" || (echo 'SHUNRI_LIPSYNC_COMMAND が未設定です' && exit 1)
	$(PYTHON) scripts/reel_poc.py --file "$(FILE)" --lipsync-backend external

quicktime-copy:
	@test -n "$(FILE)" || (echo '使い方: make quicktime-copy FILE="/path/to/reel.mp4"' && exit 1)
	$(PYTHON) scripts/quicktime_compat.py "$(FILE)"

self-check:
	$(PYTHON) -m py_compile scripts/*.py
	$(PYTHON) -c 'import json; json.load(open("config/reel_profile.json")); json.load(open("config/motion_bank.json")); json.load(open("config/lipsync.json")); json.load(open("config/gemini_voice_candidates.json")); json.load(open("config/gemini_voice_younger_candidates.json")); json.load(open("config/shunri_voice_profile.json")); print("config-check: OK")'
	PYTHONPATH=scripts $(PYTHON) scripts/self_test_reel.py
	PYTHONPATH=scripts $(PYTHON) scripts/self_test_shunri_cli.py
	$(PYTHON) scripts/self_test_remotion.py

clean:
	rm -rf outputs
