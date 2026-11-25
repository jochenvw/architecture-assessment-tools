"""Information protection: redaction, aliasing, idempotence, manual review."""

from __future__ import annotations

import json
import unittest

from _harness import TempDirTest, codes

from ada_lib import sanitize

SUB = "11111111-2222-3333-4444-555555555555"
# Built at runtime so this file itself never contains a contiguous secret-shaped literal.
FAKE_KEY = "Q" * 40
FAKE_JWT = "eyJ" + "a" * 20 + ".eyJ" + "b" * 20 + "." + "c" * 20


def scrub(text: str, aliases: sanitize.AliasMap | None = None, apply: bool = True):
    aliases = aliases or sanitize.AliasMap()
    result = sanitize.Result()
    return sanitize.process_text(text, "x.md", aliases, [], apply, result), result, aliases


class RedactionTest(unittest.TestCase):
    def test_secrets_are_redacted(self):
        text = (f"DefaultEndpointsProtocol=https;AccountName=demo;AccountKey={FAKE_KEY};\n"
                f"Authorization: Bearer {FAKE_JWT}\n"
                f"client_secret = '{FAKE_KEY}'\n"
                f"https://demo.blob.core.windows.net/c?sv=2024&sig={FAKE_KEY}\n")
        cleaned, result, _ = scrub(text)
        self.assertNotIn(FAKE_KEY, cleaned)
        self.assertNotIn(FAKE_JWT, cleaned)
        self.assertGreaterEqual(result.secrets_redacted, 3)
        self.assertEqual(result.blocking, [])

    def test_placeholders_are_not_findings(self):
        _, result, _ = scrub("api_key = <your-key>\npassword: ${DB_PASSWORD}\nsecret = changeme\n", apply=False)
        self.assertEqual(result.findings, [])

    def test_identifiers_are_aliased_consistently(self):
        rid = f"/subscriptions/{SUB}/resourceGroups/rg-claims-prod/providers/Microsoft.Search/searchServices/srch-claims"
        text = f"{rid}\nsee {rid}\nendpoint https://srch-claims.search.windows.net\nowner jane.doe@corp.test from 20.50.1.2\nsub {SUB}\n"
        cleaned, _, aliases = scrub(text)
        for raw in (SUB, "rg-claims-prod", "srch-claims", "jane.doe@corp.test", "20.50.1.2"):
            self.assertNotIn(raw, cleaned)
        self.assertIn("AZ-SUB-1", cleaned)
        self.assertEqual(cleaned.count("AZ-SEARCH-1"), 2)
        self.assertIn("@example.invalid", cleaned)
        self.assertNotIn("AZ-SUB-2", cleaned, "same subscription must keep one alias")

    def test_private_and_version_numbers_untouched(self):
        cleaned, result, _ = scrub("subnet 10.0.1.4 and version 1.2.3.4\n", apply=False)
        self.assertEqual(result.findings, [])

    def test_idempotent(self):
        text = f"/subscriptions/{SUB}/resourceGroups/rg1\nAccountKey={FAKE_KEY}\nbob@corp.test\n"
        aliases = sanitize.AliasMap()
        once, _, _ = scrub(text, aliases)
        twice, result, _ = scrub(once, aliases)
        self.assertEqual(once, twice)
        self.assertEqual([f for f in result.findings if f.severity != "manual_review"], [])

    def test_financial_figures_require_manual_review(self):
        cleaned, result, _ = scrub("Operating profit rose to $4.2bn in the quarter.\n")
        self.assertIn("$4.2bn", cleaned, "financial figures are never silently rewritten")
        self.assertEqual([f.kind for f in result.blocking], ["financial_figure"])


class PackageProtectionTest(TempDirTest):
    def test_check_blocks_sensitive_content_and_apply_fixes_it(self):
        out = self.copy_example()
        report = out / "discovery-report.md"
        report.write_text(report.read_text(encoding="utf-8") + f"\nSubscription {SUB}; AccountKey={FAKE_KEY}\n", encoding="utf-8")
        self.assertIn("sensitive-secret", codes(out))
        self.assertIn("sensitive-identifier", codes(out))
        (out / "_work").mkdir()
        result, _ = sanitize.run([report], out, sanitize.AliasMap(out / "_work" / "alias-map.json"), None, apply=True)
        self.assertTrue(result.secrets_redacted)
        self.assertFalse({"sensitive-secret", "sensitive-identifier"} & codes(out))

    def test_allowlist_resolves_manual_review(self):
        out = self.copy_example()
        report = out / "discovery-report.md"
        report.write_text(report.read_text(encoding="utf-8") + "\nPublished threshold: EUR 5 million (public filing).\n", encoding="utf-8")
        self.assertIn("sensitive-manual_review", codes(out))
        (out / "_work").mkdir()
        (out / "_work" / "sanitize-allowlist.json").write_text(json.dumps(
            {"allow": [{"match": "EUR 5 million", "reason": "Published public threshold", "file": "discovery-report.md"}]}), encoding="utf-8")
        self.assertNotIn("sensitive-manual_review", codes(out))


class InternalTermsTest(unittest.TestCase):
    def test_remote_owner_and_repo_become_terms(self):
        cases = {
            "https://github.com/acme-corp/claims-bot.git": {("acme-corp", "ORG"), ("claims-bot", "APP")},
            "git@github.com:acme-corp/claims-bot.git": {("acme-corp", "ORG"), ("claims-bot", "APP")},
            "https://dev.azure.com/acme-corp/Claims/_git/claims-bot": {("acme-corp", "ORG"), ("Claims", "ORG"), ("claims-bot", "APP")},
            "https://acme-corp.visualstudio.com/Claims/_git/claims-bot": {("acme-corp", "ORG"), ("Claims", "ORG"), ("claims-bot", "APP")},
        }
        for remote, expected in cases.items():
            with self.subTest(remote=remote):
                self.assertEqual(set(sanitize.identity_terms(None, remote)), expected)

    def test_registered_terms_are_aliased_but_public_names_are_not(self):
        aliases = sanitize.AliasMap()
        self.assertEqual(aliases.register_term("Acme-Corp", "ORG"), "ORG-1")
        self.assertIsNone(aliases.register_term("Microsoft", "ORG"))
        cleaned, _, _ = scrub("acme-corp runs on Microsoft Foundry; ACME-CORP owns it.", aliases)
        self.assertEqual(cleaned, "ORG-1 runs on Microsoft Foundry; ORG-1 owns it.")


if __name__ == "__main__":
    unittest.main()
