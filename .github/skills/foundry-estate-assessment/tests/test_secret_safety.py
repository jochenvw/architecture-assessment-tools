"""Secret safety: secrets are redacted before evaluation and persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _harness import Pipeline
from foundry_estate_assessment.evidence import EvidenceStore
from foundry_estate_assessment.sanitize import REDACTED, contains_secret_markers, sanitize


class SanitizeTest(unittest.TestCase):
    def test_secret_keys_are_redacted(self):
        raw = {
            "properties": {
                "primaryKey": "abc123",
                "connectionString": "AccountName=x;AccountKey=supersecret==;",
                "apiKey": "zzz",
                "publicNetworkAccess": "Disabled",
            },
            "value": "kv-secret-material",
        }
        clean = sanitize(raw)
        self.assertEqual(clean["properties"]["primaryKey"], REDACTED)
        self.assertEqual(clean["properties"]["apiKey"], REDACTED)
        self.assertEqual(clean["value"], REDACTED)
        # Non-secret configuration is preserved.
        self.assertEqual(clean["properties"]["publicNetworkAccess"], "Disabled")

    def test_input_is_not_mutated(self):
        raw = {"apiKey": "zzz"}
        sanitize(raw)
        self.assertEqual(raw["apiKey"], "zzz")

    def test_sas_and_bearer_tokens_stripped(self):
        url = "https://acct.blob.core.windows.net/c?sv=2021&sig=DEADBEEFsignature&sp=r"
        clean = sanitize({"target": url, "auth": "Bearer eyJhbGciOiJ.payload.sig"})
        self.assertNotIn("DEADBEEFsignature", json.dumps(clean))
        self.assertNotIn("eyJhbGciOiJ", json.dumps(clean))

    def test_safe_lookalike_keys_kept(self):
        clean = sanitize({"tokenLimit": 1000, "tokenCredential": "type"})
        self.assertEqual(clean["tokenLimit"], 1000)
        self.assertEqual(clean["tokenCredential"], "type")

    def test_marker_detector(self):
        self.assertTrue(contains_secret_markers("x AccountKey=abc"))
        self.assertFalse(contains_secret_markers("publicNetworkAccess Disabled"))


class EvidencePersistenceTest(unittest.TestCase):
    def test_persisted_raw_is_sanitized(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(Path(tmp) / "raw")
            raw = {"properties": {"accountKey": "TOPSECRET==", "sku": "S0"}}
            prov = store.persist_raw("/sub/x", "keyvault", raw, "2024-01-01")
            written = Path(prov["raw_path"]).read_text(encoding="utf-8")
            self.assertNotIn("TOPSECRET", written)
            self.assertIn(REDACTED, written)
            self.assertTrue(prov["raw_sha256"])

    def test_no_raw_evidence_writes_nothing_but_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = EvidenceStore(Path(tmp) / "raw", no_raw_evidence=True)
            prov = store.persist_raw("/sub/x", "apim", {"apiKey": "s"}, "v")
            self.assertIsNone(prov["raw_path"])
            self.assertTrue(prov["raw_sha256"])


class EndToEndSecretScanTest(unittest.TestCase):
    def test_no_secret_markers_in_any_persisted_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                raw_dir = Path(tmp) / "raw"
                for path in raw_dir.glob("*.json"):
                    text = path.read_text(encoding="utf-8")
                    self.assertFalse(contains_secret_markers(text), f"secret markers in {path.name}")
                # No APIM subscription-key field should ever be stored as a fact.
                for ev in pipe.db.list_evidence(pipe.snapshot_id):
                    serialized = json.dumps(ev["fact"]).lower()
                    self.assertNotIn("subscriptionkey", serialized)
                    self.assertNotIn("primarykey", serialized)
            finally:
                pipe.close()


if __name__ == "__main__":
    unittest.main()
