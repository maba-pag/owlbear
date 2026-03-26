import subprocess, sys, pathlib
args = [sys.executable, '-m', 'pytest', 'tests/', '-m', 'not api', '-q', '--tb=line', '--ignore', 'tests/benchmarks/test_entity_extractor_corpus.py', '--ignore', 'tests/test_957_notify_escalate_executors.py', '--ignore', 'tests/test_improvement_proposals.py', '--ignore', 'tests/test_security_audit_log.py']
r = subprocess.run(args, capture_output=True, text=True, timeout=300)
pathlib.Path('docs/scratch/pytest-892.txt').write_text(r.stdout + chr(10) + r.stderr)
print('exit:', r.returncode)