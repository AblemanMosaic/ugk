.PHONY: test readme verify clean

test:
	PYTHONUNBUFFERED=1 python -m ugk.conformance.run_gates_batch

readme:
	python readme_gen.py

verify:
	./verify_release.sh

check-readme:
	python readme_gen.py --check

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
