"""Optional Azure discovery with a fake runner: robust, read-only, aliased."""

from __future__ import annotations

import json
import unittest

from _harness import TempDirTest, load

from ada_lib import azure, checks, sanitize, workspace

SUB = "11111111-2222-3333-4444-555555555555"
RG = "rg-claims-test"
FOUNDRY_ID = f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/accounts/aif-claims-test"
SEARCH_ID = f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.Search/searchServices/srch-claims-test"


class FakeRunner:
    """Answers by command shape; records every argv. Enforces the guard like the real runner."""

    def __init__(self, rbac_outcome: str = "ok", auth_ok: bool = True, with_app_insights: bool = False):
        self.calls: list[list[str]] = []
        self.rbac_outcome = rbac_outcome
        self.auth_ok = auth_ok
        self.with_app_insights = with_app_insights

    def __call__(self, argv):
        self.calls.append(argv)
        allowed, reason = azure.guard(argv)
        if not allowed:
            return azure.RunResult("blocked_by_guard", detail=reason)
        cmd = " ".join(argv)
        if cmd == "az version":
            return azure.RunResult("ok", {"azure-cli": "2.70.0"})
        if cmd.startswith("az account show"):
            return azure.RunResult("ok", {"tenant": SUB}) if self.auth_ok else azure.RunResult("not_authenticated", detail="Please run 'az login'")
        if cmd.startswith("az group show"):
            return azure.RunResult("ok", {"location": "westeurope"})
        if cmd.startswith("az resource list"):
            appi = [{"id": f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.Insights/components/appi-claims-test",
                     "name": "appi-claims-test", "type": "Microsoft.Insights/components", "kind": "web", "location": "westeurope"}]
            return azure.RunResult("ok", [
                {"id": FOUNDRY_ID, "name": "aif-claims-test", "type": "Microsoft.CognitiveServices/accounts", "kind": "AIServices", "location": "westeurope"},
                {"id": SEARCH_ID, "name": "srch-claims-test", "type": "Microsoft.Search/searchServices", "kind": None, "location": "westeurope"},
            ] + (appi if self.with_app_insights else []))
        if cmd.startswith("az resource show") and FOUNDRY_ID in cmd:
            return azure.RunResult("ok", {"publicNetworkAccess": "Disabled", "disableLocalAuth": True, "customSubDomain": True,
                                          "note": "endpoint https://aif-claims-test.cognitiveservices.azure.com"})
        if cmd.startswith("az resource show") and SEARCH_ID in cmd:
            return azure.RunResult("ok", {"publicNetworkAccess": "Enabled", "privateEndpointConnections": 0})
        if "deployment list" in cmd:
            return azure.RunResult("ok", [{"name": "gpt-review", "model": "gpt-4o", "version": "2024-11-20", "sku": "GlobalStandard", "capacity": 50}])
        if "diagnostic-settings list" in cmd:
            return azure.RunResult("empty", [])
        if cmd.startswith("az rest"):
            return azure.RunResult("ok", [{"name": "claims-index", "fieldCount": 9, "vectorFields": 1}])
        if "role assignment list" in cmd:
            if self.rbac_outcome != "ok":
                return azure.RunResult(self.rbac_outcome, detail=f"AuthorizationFailed on {FOUNDRY_ID}")
            return azure.RunResult("ok", [{"principalType": "ServicePrincipal", "role": "Cognitive Services User", "scope": FOUNDRY_ID, "principal": SUB}])
        if "policy state summarize" in cmd:
            return azure.RunResult("ok", {"nonCompliantResources": 1, "nonCompliantPolicies": 1, "assignments": []})
        return azure.RunResult("error", detail="unexpected command")


class AzureCollectorTest(TempDirTest):
    def setUp(self):
        super().setUp()
        repo = self.copy_fixture("malicious-repo")
        self.out = self.tmp / "out"
        workspace.init(repo, self.out, ["azure-agent"])
        self.scope = azure.Scope(SUB, RG, "test", "platform owner")

    def _collect(self, runner):
        collector = azure.Collector(self.out, self.scope, runner)
        summary = collector.collect()
        azure.write_collection(self.out, collector, summary)
        return collector

    def test_collection_is_read_only_and_aliased(self):
        runner = FakeRunner()
        collector = self._collect(runner)
        self.assertTrue(all(azure.guard(argv)[0] for argv in runner.calls))
        self.assertEqual({r["alias"] for r in collector.resources} >= {"AZ-AISVC-1", "AZ-SEARCH-1"}, True)
        package_text = "".join((self.out / n).read_text(encoding="utf-8")
                               for n in ("azure-configuration.json", "evidence.json", "manifest.json"))
        for raw in (SUB, RG, "aif-claims-test", "srch-claims-test"):
            self.assertNotIn(raw, package_text)
        manifest = load(self.out, "manifest.json")
        self.assertIn("azure_configuration", manifest["discovery_modes"])
        self.assertTrue(manifest["azure_scope"]["authorised"])

    def test_collected_output_passes_schema_and_reference_gates(self):
        self._collect(FakeRunner())
        from ada_lib import render
        render.render(self.out)
        bad = {i.code for i in checks.run(self.out, allow_incomplete=True) if i.level == "error"}
        self.assertFalse(bad & {"schema", "unresolved-evidence", "azure-mode-undeclared", "azure-unauthorised",
                                "sensitive-secret", "sensitive-identifier", "render-stale"}, bad)

    def test_internal_names_in_prose_are_aliased(self):
        self._collect(FakeRunner())
        manifest = load(self.out, "manifest.json")
        self.assertEqual(manifest["repository"]["name"], "APP-1")
        report = self.out / "discovery-report.md"
        report.write_text(report.read_text(encoding="utf-8") + f"\nDeployed to {RG} by malicious-repo.\n", encoding="utf-8")
        result, _ = sanitize.run(workspace.package_files(self.out), self.out,
                                 sanitize.AliasMap(self.out / "_work" / "alias-map.json"), None, apply=True)
        text = report.read_text(encoding="utf-8")
        self.assertNotIn(RG, text)
        self.assertNotIn("malicious-repo", text)
        self.assertIn("Deployed to AZ-RG-1 by APP-1.", text)
        self.assertNotIn("AZ-RG-2", (self.out / "_work" / "alias-map.json").read_text(encoding="utf-8"))

    def test_app_insights_components_are_queued_for_telemetry(self):
        collector = self._collect(FakeRunner(with_app_insights=True))
        self.assertEqual(collector.app_insights, ["appi-claims-test"])

    def test_forbidden_rbac_is_recorded_not_fatal(self):
        collector = self._collect(FakeRunner(rbac_outcome="forbidden"))
        attempts = [a for a in collector.attempts if a["collector"] == "rbac"]
        self.assertEqual(attempts[0]["outcome"], "forbidden")
        self.assertNotIn(SUB, json.dumps(collector.attempts))
        self.assertTrue(collector.resources)

    def test_unauthenticated_stops_after_preflight(self):
        runner = FakeRunner(auth_ok=False)
        collector = self._collect(runner)
        self.assertEqual(collector.resources, [])
        self.assertEqual(len(runner.calls), 2)

    def test_scope_must_be_explicit(self):
        with self.assertRaises(ValueError):
            azure.Scope("", RG, "test", "platform owner").validate()
        with self.assertRaises(ValueError):
            azure.Scope(SUB, RG, "prod-ish", "platform owner").validate()

    def test_missing_cli_is_reported(self):
        def no_cli(argv):
            return azure.RunResult("cli_missing", detail="Azure CLI not found on PATH")
        pre = azure.Collector(self.out, self.scope, no_cli).preflight()
        self.assertFalse(pre["cli_available"])
        self.assertFalse(pre["resource_group_accessible"])

    def test_telemetry_is_aggregate_only_and_measured(self):
        calls = []

        def runner(argv):
            calls.append(argv)
            self.assertTrue(azure.guard(argv)[0])
            if "requests |" in argv[argv.index("--analytics-query") + 1]:
                return azure.RunResult("ok", {"tables": [{"columns": [{"name": "avg_daily"}, {"name": "p95_ms"}], "rows": [[120.5, 2300]]}]})
            return azure.RunResult("forbidden", detail="AuthorizationFailed")

        dry = azure.collect_telemetry(self.out, self.scope, "appi-claims-test", 30, runner, execute=False)
        self.assertEqual(calls, [])
        self.assertTrue(all(a["detail"] == "dry run" for a in dry["attempts"]))
        tel = azure.collect_telemetry(self.out, self.scope, "appi-claims-test", 30, runner, execute=True)
        self.assertEqual(azure.telemetry_to_package(self.out, self.scope, tel), 1)
        wl = load(self.out, "workload-characteristics.json")["characteristics"]
        self.assertEqual({w["value_type"] for w in wl}, {"measured"})
        text = (self.out / "evidence.json").read_text(encoding="utf-8") + (self.out / "manifest.json").read_text(encoding="utf-8")
        self.assertNotIn("appi-claims-test", text)
        self.assertNotIn("telemetry-unauthorised", {i.code for i in checks.run(self.out, allow_incomplete=True)})
        for kql in azure.TELEMETRY_QUERIES.values():
            self.assertIn("summarize", kql)


if __name__ == "__main__":
    unittest.main()
