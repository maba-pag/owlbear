"""RED phase placeholder - implementation belongs in task #912.

The corpus fixture is intentionally absent here so that the contract tests in
tests/benchmarks/test_entity_extractor_corpus.py fail at import time (AC 5).
Task #912 will replace this file with the real CorpusSample / GoldEntity /
ENTITY_EXTRACTOR_CORPUS / load_corpus implementation.
"""

_msg = "RED placeholder: corpus fixture not yet implemented. See task #912."
raise ImportError(_msg)
