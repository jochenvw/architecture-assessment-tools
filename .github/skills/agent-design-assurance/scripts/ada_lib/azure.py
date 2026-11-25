"""Optional, read-only Azure discovery.

Safety model
------------
* Nothing runs without the requester's explicit "yes, use the Azure CLI" and an
  explicit scope: subscription and resource group (environment defaults to
  ``unknown``, authoriser to ``requester``). That one consent covers both
  configuration and aggregated telemetry.
* ``collect``/``telemetry`` are dry runs unless ``--execute`` is given.
* Every command passes :func:`guard` (allow-list of read verbs, deny-list of
  secret-bearing or mutating command groups) before it may run.
* ``--subscription`` is passed per command; ``az account set`` is never used.
* Projections (``--query``) select configuration properties only. No keys,
  connection strings, app settings or business data are requested.
* Real names/IDs are replaced by aliases before anything is written to the
  package; the alias map stays in ``_work/``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from . import SCHEMA_VERSION, sanitize, workspace
from .util import dump_json, load_json, utc_now

ENVIRONMENTS = ["development", "test", "acceptance", "production", "shared", "unknown"]

ALLOWED_VERBS = {"show", "list", "query", "summarize", "version"}
DENIED_TOKENS = {
    "keys", "key", "list-keys", "secret", "secrets", "token", "get-access-token", "connection-string",
    "show-connection-string", "list-connection-strings", "credential", "credentials", "login", "logout", "set",
    "create", "update", "delete", "assign", "register", "unregister", "invoke", "invoke-action", "start", "stop",
    "restart", "deploy", "purge", "regenerate", "regenerate-key", "upload", "download", "appsettings",
    "generate-sas", "sas", "export", "import", "reset", "run-command", "ssh", "exec", "console", "browse", "tunnel",
    "password", "publishing-profile", "list-publishing-profiles", "list-publishing-credentials", "backup", "restore",
}
DENIED_OPTIONS = {"--show-secrets", "--password", "--account-key", "--sas-token", "--connection-string", "--auth-mode", "--include-secrets"}
SEARCH_REST = re.compile(r"^https://[a-z0-9][a-z0-9-]{0,62}\.search\.windows\.net/(indexes|indexers|skillsets)(/[A-Za-z0-9._-]+)?(\?[^\s]*)?$", re.I)


def guard(argv: list[str]) -> tuple[bool, str]:
    """Return (allowed, reason) for an ``az`` argument vector."""
    if not argv or argv[0] != "az":
        return False, "only Azure CLI commands are permitted"
    path: list[str] = []
    for token in argv[1:]:
        if token.startswith("-"):
            break
        path.append(token.lower())
    if not path:
        return False, "empty command"
    for token in argv[1:]:
        if token.split("=", 1)[0].lower() in DENIED_OPTIONS:
            return False, f"option {token} is not permitted"
    denied = [t for t in path if t in DENIED_TOKENS]
    if denied:
        return False, f"command group/verb '{denied[0]}' is not permitted (read-only, no secrets)"
    if path[0] == "rest":
        method = _flag(argv, "--method") or _flag(argv, "-m") or "get"
        url = _flag(argv, "--url") or _flag(argv, "-u") or ""
        if method.lower() != "get":
            return False, "az rest is limited to GET"
        if "datasources" in url.lower() or not SEARCH_REST.match(url):
            return False, "az rest is limited to AI Search index/indexer/skillset definitions"
        return True, "ok"
    if path[-1] not in ALLOWED_VERBS:
        return False, f"verb '{path[-1]}' is not an allowed read verb ({', '.join(sorted(ALLOWED_VERBS))})"
    return True, "ok"


def _flag(argv: list[str], flag: str) -> str | None:
    for i, token in enumerate(argv):
        if token == flag and i + 1 < len(argv):
            return argv[i + 1]
        if token.startswith(flag + "="):
            return token.split("=", 1)[1]
    return None


@dataclass
class RunResult:
    outcome: str  # ok | empty | forbidden | not_found | not_authenticated | extension_missing | cli_missing | timeout | blocked_by_guard | error
    data: Any = None
    detail: str | None = None


class Runner(Protocol):
    def __call__(self, argv: list[str]) -> RunResult: ...


def classify(stderr: str) -> str:
    low = stderr.lower()
    if "az login" in low or "please run 'az login'" in low or "authenticationfailed" in low or "interactive authentication" in low:
        return "not_authenticated"
    if any(m in low for m in ("authorizationfailed", "does not have authorization", "forbidden", "(403)", "insufficient privileges", "accessdenied")):
        return "forbidden"
    if any(m in low for m in ("resourcenotfound", "resourcegroupnotfound", "not found", "(404)", "subscriptionnotfound")):
        return "not_found"
    if ("is not in the" in low and "command group" in low) or ("extension" in low and ("not installed" in low or "dynamic install" in low)):
        return "extension_missing"
    return "error"


def subprocess_runner(timeout: float = 120.0) -> Runner:
    az = shutil.which("az") or shutil.which("az.cmd")

    def _run(argv: list[str]) -> RunResult:
        allowed, reason = guard(argv)
        if not allowed:
            return RunResult("blocked_by_guard", detail=reason)
        if not az:
            return RunResult("cli_missing", detail="Azure CLI not found on PATH")
        try:
            proc = subprocess.run([az, *argv[1:], "--only-show-errors", "-o", "json"], capture_output=True, text=True,
                                  timeout=timeout, shell=False,
                                  env=None)
        except subprocess.TimeoutExpired:
            return RunResult("timeout", detail=f"timed out after {timeout:.0f}s")
        except OSError as exc:
            return RunResult("cli_missing", detail=str(exc))
        if proc.returncode != 0:
            outcome = classify(proc.stderr or "")
            return RunResult(outcome, detail=_short(proc.stderr))
        text = (proc.stdout or "").strip()
        if not text:
            return RunResult("empty", data=None)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return RunResult("error", detail="non-JSON output")
        return RunResult("empty" if data in (None, [], {}) else "ok", data=data)

    return _run


def _short(stderr: str | None) -> str:
    text = (stderr or "").strip().splitlines()
    first = next((l for l in text if l.strip()), "")
    first = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "<guid>", first)
    first = re.sub(r"/subscriptions/[^\s'\"]+", "<resource-id>", first)
    return first[:200]


# --------------------------------------------------------------------------- collectors

def _len(expr: str) -> str:
    return f"length({expr}||`[]`)"


PROJECTIONS: dict[str, str] = {
    "microsoft.cognitiveservices/accounts": "{kind:kind,sku:sku.name,identity:identity.type,publicNetworkAccess:properties.publicNetworkAccess,disableLocalAuth:properties.disableLocalAuth,networkDefaultAction:properties.networkAcls.defaultAction,privateEndpointConnections:" + _len("properties.privateEndpointConnections") + ",customSubDomain:properties.customSubDomainName!=null,allowProjectManagement:properties.allowProjectManagement,restrictOutboundNetworkAccess:properties.restrictOutboundNetworkAccess,encryptionKeySource:properties.encryption.keySource}",
    "microsoft.search/searchservices": "{sku:sku.name,identity:identity.type,replicaCount:properties.replicaCount,partitionCount:properties.partitionCount,publicNetworkAccess:properties.publicNetworkAccess,disableLocalAuth:properties.disableLocalAuth,authOptions:properties.authOptions,semanticSearch:properties.semanticSearch,networkBypass:properties.networkRuleSet.bypass,ipRules:" + _len("properties.networkRuleSet.ipRules") + ",privateEndpointConnections:" + _len("properties.privateEndpointConnections") + ",cmkEnforcement:properties.encryptionWithCmk.enforcement}",
    "microsoft.storage/storageaccounts": "{kind:kind,sku:sku.name,identity:identity.type,publicNetworkAccess:properties.publicNetworkAccess,allowBlobPublicAccess:properties.allowBlobPublicAccess,allowSharedKeyAccess:properties.allowSharedKeyAccess,minimumTlsVersion:properties.minimumTlsVersion,networkDefaultAction:properties.networkAcls.defaultAction,isHnsEnabled:properties.isHnsEnabled,privateEndpointConnections:" + _len("properties.privateEndpointConnections") + "}",
    "microsoft.documentdb/databaseaccounts": "{kind:kind,identity:identity.type,publicNetworkAccess:properties.publicNetworkAccess,disableLocalAuth:properties.disableLocalAuth,consistency:properties.consistencyPolicy.defaultConsistencyLevel,locations:" + _len("properties.locations") + ",multipleWriteLocations:properties.enableMultipleWriteLocations,automaticFailover:properties.enableAutomaticFailover,backupPolicy:properties.backupPolicy.type,capabilities:properties.capabilities[].name,privateEndpointConnections:" + _len("properties.privateEndpointConnections") + "}",
    "microsoft.keyvault/vaults": "{sku:properties.sku.name,rbacAuthorization:properties.enableRbacAuthorization,softDelete:properties.enableSoftDelete,purgeProtection:properties.enablePurgeProtection,publicNetworkAccess:properties.publicNetworkAccess,networkDefaultAction:properties.networkAcls.defaultAction,privateEndpointConnections:" + _len("properties.privateEndpointConnections") + "}",
    "microsoft.web/sites": "{kind:kind,identity:identity.type,httpsOnly:properties.httpsOnly,publicNetworkAccess:properties.publicNetworkAccess,vnetIntegration:properties.virtualNetworkSubnetId!=null,vnetRouteAllEnabled:properties.vnetRouteAllEnabled,clientCertEnabled:properties.clientCertEnabled,state:properties.state}",
    "microsoft.app/containerapps": "{identity:identity.type,ingressExternal:properties.configuration.ingress.external,allowInsecure:properties.configuration.ingress.allowInsecure,minReplicas:properties.template.scale.minReplicas,maxReplicas:properties.template.scale.maxReplicas,scaleRules:properties.template.scale.rules[].name,revisionsMode:properties.configuration.activeRevisionsMode,workloadProfile:properties.workloadProfileName,secretCount:" + _len("properties.configuration.secrets") + ",keyVaultSecretRefs:" + _len("properties.configuration.secrets[?keyVaultUrl]") + ",containers:properties.template.containers[].{cpu:resources.cpu,memory:resources.memory,probes:length(probes||`[]`),envNames:env[].name}}",
    "microsoft.app/managedenvironments": "{vnetInternal:properties.vnetConfiguration.internal,infrastructureSubnet:properties.vnetConfiguration.infrastructureSubnetId!=null,zoneRedundant:properties.zoneRedundant,workloadProfiles:properties.workloadProfiles[].workloadProfileType,logsDestination:properties.appLogsConfiguration.destination,publicNetworkAccess:properties.publicNetworkAccess}",
    "microsoft.apimanagement/service": "{sku:sku.name,capacity:sku.capacity,identity:identity.type,virtualNetworkType:properties.virtualNetworkType,publicNetworkAccess:properties.publicNetworkAccess,zones:zones}",
    "microsoft.insights/components": "{workspaceBased:properties.WorkspaceResourceId!=null,ingestionMode:properties.IngestionMode,retentionInDays:properties.RetentionInDays,disableLocalAuth:properties.DisableLocalAuth,samplingPercentage:properties.SamplingPercentage,publicNetworkAccessForIngestion:properties.publicNetworkAccessForIngestion,publicNetworkAccessForQuery:properties.publicNetworkAccessForQuery}",
    "microsoft.operationalinsights/workspaces": "{sku:properties.sku.name,retentionInDays:properties.retentionInDays,dailyQuotaGb:properties.workspaceCapping.dailyQuotaGb,publicNetworkAccessForIngestion:properties.publicNetworkAccessForIngestion,publicNetworkAccessForQuery:properties.publicNetworkAccessForQuery}",
    "microsoft.network/privateendpoints": "{groupIds:properties.privateLinkServiceConnections[].properties.groupIds[],connectionState:properties.privateLinkServiceConnections[].properties.privateLinkServiceConnectionState.status,target:properties.privateLinkServiceConnections[].properties.privateLinkServiceId,subnet:properties.subnet.id,dnsZoneGroups:" + _len("properties.privateDnsZoneGroups") + "}",
    "microsoft.network/virtualnetworks": "{addressSpaceCount:" + _len("properties.addressSpace.addressPrefixes") + ",subnets:properties.subnets[].{name:name,delegations:properties.delegations[].properties.serviceName,nsg:properties.networkSecurityGroup!=null,routeTable:properties.routeTable!=null,privateEndpointPolicies:properties.privateEndpointNetworkPolicies},peerings:" + _len("properties.virtualNetworkPeerings") + ",ddosProtection:properties.enableDdosProtection}",
    "microsoft.network/networksecuritygroups": "{rules:properties.securityRules[].{direction:properties.direction,access:properties.access,priority:properties.priority,protocol:properties.protocol,sourceIsInternet:properties.sourceAddressPrefix=='Internet'||properties.sourceAddressPrefix=='*',destinationPort:properties.destinationPortRange}}",
    "microsoft.containerregistry/registries": "{sku:sku.name,adminUserEnabled:properties.adminUserEnabled,publicNetworkAccess:properties.publicNetworkAccess,anonymousPull:properties.anonymousPullEnabled,privateEndpointConnections:" + _len("properties.privateEndpointConnections") + "}",
    "microsoft.machinelearningservices/workspaces": "{kind:kind,identity:identity.type,publicNetworkAccess:properties.publicNetworkAccess,managedNetworkIsolation:properties.managedNetwork.isolationMode,hbiWorkspace:properties.hbiWorkspace,privateEndpointConnections:" + _len("properties.privateEndpointConnections") + "}",
    "microsoft.cognitiveservices/accounts/projects": "{identity:identity.type,isDefault:properties.isDefault}",
    "microsoft.managedidentity/userassignedidentities": "{type:type}",
}
DEFAULT_PROJECTION = "{kind:kind,sku:sku.name,identity:identity.type,publicNetworkAccess:properties.publicNetworkAccess,provisioningState:properties.provisioningState}"
DIAGNOSTIC_TYPES = {
    "microsoft.cognitiveservices/accounts", "microsoft.search/searchservices", "microsoft.documentdb/databaseaccounts",
    "microsoft.keyvault/vaults", "microsoft.apimanagement/service", "microsoft.web/sites", "microsoft.app/managedenvironments",
    "microsoft.storage/storageaccounts", "microsoft.containerregistry/registries",
}


@dataclass
class Scope:
    subscription: str
    resource_group: str
    environment: str
    authorised_by: str
    search_api_version: str = "2024-07-01"

    def validate(self) -> None:
        missing = [k for k in ("subscription", "resource_group", "environment", "authorised_by") if not getattr(self, k)]
        if missing:
            raise ValueError(f"Explicit Azure scope required; missing: {', '.join('--' + m.replace('_', '-') for m in missing)}")
        if self.environment not in ENVIRONMENTS:
            raise ValueError(f"--environment must be one of {ENVIRONMENTS}")


def plan_commands(scope: Scope) -> list[dict[str, Any]]:
    """Command templates (placeholders, not values) that `collect` may run."""
    sub, rg = "{subscription}", "{resource_group}"
    rows = [
        ("preflight", ["az", "version"]),
        ("preflight", ["az", "account", "show", "--query", "{tenant:tenantId,user:user.type}"]),
        ("preflight", ["az", "group", "show", "--name", rg, "--subscription", sub, "--query", "{location:location}"]),
        ("inventory", ["az", "resource", "list", "--resource-group", rg, "--subscription", sub, "--query", "[].{id:id,name:name,type:type,kind:kind,location:location}"]),
        ("configuration", ["az", "resource", "show", "--ids", "{resource_id}", "--query", "<per-type projection>"]),
        ("model_deployments", ["az", "cognitiveservices", "account", "deployment", "list", "--name", "{account}", "--resource-group", rg, "--subscription", sub, "--query", "<deployment projection>"]),
        ("diagnostics", ["az", "monitor", "diagnostic-settings", "list", "--resource", "{resource_id}", "--query", "<category projection>"]),
        ("rbac", ["az", "role", "assignment", "list", "--resource-group", rg, "--subscription", sub, "--include-inherited", "--query", "<role projection>"]),
        ("policy", ["az", "policy", "state", "summarize", "--resource-group", rg, "--subscription", sub, "--query", "<summary projection>"]),
        ("search_definitions", ["az", "rest", "--method", "get", "--url", "https://{search}.search.windows.net/indexes?api-version=" + scope.search_api_version, "--resource", "https://search.azure.com", "--query", "<schema shape projection>"]),
    ]
    return [{"collector": c, "command_template": " ".join(argv), "allowed": guard([a.replace("{", "x").replace("}", "x") if a.startswith("https://{") else a for a in argv])[0]} for c, argv in rows]


class Collector:
    def __init__(self, out: Path, scope: Scope, runner: Runner, include_search_definitions: bool = True):
        self.out = Path(out)
        self.scope = scope
        self.runner = runner
        self.include_search = include_search_definitions
        self.aliases = sanitize.AliasMap(workspace.work_dir(out) / "alias-map.json")
        self.attempts: list[dict[str, Any]] = []
        self.resources: list[dict[str, Any]] = []
        self.app_insights: list[str] = []
        self.evidence: list[dict[str, Any]] = []
        self.now = utc_now()

    # -- helpers
    def _template(self, argv: list[str]) -> str:
        text = " ".join(argv)
        text = text.replace(self.scope.subscription, "{subscription}").replace(self.scope.resource_group, "{resource_group}")
        return str(sanitize.clean_value(text, self.aliases))

    def _run(self, collector: str, argv: list[str], target: str | None = None) -> RunResult:
        result = self.runner(argv)
        self.attempts.append({
            "collector": collector, "target": target, "command_template": self._template(argv),
            "outcome": result.outcome, "detail": str(sanitize.clean_value(result.detail, self.aliases)) if result.detail else None,
        })
        return result

    def _sub_args(self) -> list[str]:
        return ["--subscription", self.scope.subscription]

    # -- steps
    def preflight(self) -> dict[str, Any]:
        version = self._run("preflight", ["az", "version"])
        account = self._run("preflight", ["az", "account", "show", "--query", "{tenant:tenantId,user:user.type}"]) if version.outcome == "ok" else version
        group = self._run("preflight", ["az", "group", "show", "--name", self.scope.resource_group, *self._sub_args(), "--query", "{location:location}"]) if account.outcome == "ok" else account
        return {
            "cli_available": version.outcome not in ("cli_missing",),
            "authenticated": account.outcome == "ok",
            "resource_group_accessible": group.outcome == "ok",
            "outcomes": {"version": version.outcome, "account": account.outcome, "resource_group": group.outcome},
        }

    def collect(self) -> dict[str, Any]:
        pre = self.preflight()
        sub_alias = self.aliases.alias(self.scope.subscription, "AZ-SUB")
        rg_alias = self.aliases.alias("rg:" + self.scope.resource_group, "AZ-RG")
        self.aliases.register_name(self.scope.resource_group, rg_alias)
        if not re.fullmatch(sanitize.GUID, self.scope.subscription):
            self.aliases.register_name(self.scope.subscription, sub_alias)
        if not pre["resource_group_accessible"]:
            self.aliases.save()
            return {"preflight": pre, "subscription_alias": sub_alias, "resource_group_alias": rg_alias}

        listing = self._run("inventory", ["az", "resource", "list", "--resource-group", self.scope.resource_group, *self._sub_args(),
                                          "--query", "[].{id:id,name:name,type:type,kind:kind,location:location}"])
        items = listing.data if listing.outcome == "ok" and isinstance(listing.data, list) else []
        for item in items:
            rtype = (item.get("type") or "").lower()
            alias = self.aliases.alias(f"name:{item['name']}", "AZ-" + sanitize.type_token(rtype))
            self.aliases.register_name(item["name"], alias)
            if rtype == "microsoft.insights/components":
                self.app_insights.append(item["name"])

        for item in sorted(items, key=lambda i: ((i.get("type") or "").lower(), i.get("name") or "")):
            self._collect_resource(item, rg_alias)
        self._collect_rbac(rg_alias)
        self._collect_policy(rg_alias)
        self.aliases.save()
        return {"preflight": pre, "subscription_alias": sub_alias, "resource_group_alias": rg_alias, "resources": len(self.resources)}

    def _collect_resource(self, item: dict[str, Any], rg_alias: str) -> None:
        rtype = (item.get("type") or "").lower()
        alias = self.aliases.known_names()[item["name"].lower()]
        projection = PROJECTIONS.get(rtype, DEFAULT_PROJECTION)
        detail = self._run("configuration", ["az", "resource", "show", "--ids", item["id"], "--query", projection], alias)
        props: dict[str, Any] = sanitize.clean_value(detail.data, self.aliases) if detail.outcome == "ok" and isinstance(detail.data, dict) else {}
        if detail.outcome not in ("ok", "empty"):
            props["_collection_outcome"] = detail.outcome

        if rtype == "microsoft.cognitiveservices/accounts":
            dep = self._run("model_deployments", ["az", "cognitiveservices", "account", "deployment", "list", "--name", item["name"],
                                                  "--resource-group", self.scope.resource_group, *self._sub_args(), "--query",
                                                  "[].{name:name,model:properties.model.name,version:properties.model.version,format:properties.model.format,sku:sku.name,capacity:sku.capacity,raiPolicy:properties.raiPolicyName,versionUpgradeOption:properties.versionUpgradeOption}"], alias)
            if dep.outcome in ("ok", "empty"):
                props["model_deployments"] = sanitize.clean_value(dep.data or [], self.aliases)
        if rtype in DIAGNOSTIC_TYPES:
            diag = self._run("diagnostics", ["az", "monitor", "diagnostic-settings", "list", "--resource", item["id"], "--query",
                                             "[].{logCategories:logs[?enabled].category,logCategoryGroups:logs[?enabled].categoryGroup,metrics:metrics[?enabled].category,toWorkspace:workspaceId!=null,toStorage:storageAccountId!=null,toEventHub:eventHubAuthorizationRuleId!=null}"], alias)
            if diag.outcome in ("ok", "empty"):
                props["diagnostic_settings"] = sanitize.clean_value(diag.data or [], self.aliases)
        if rtype == "microsoft.search/searchservices" and self.include_search:
            url = f"https://{item['name']}.search.windows.net/indexes?api-version={self.scope.search_api_version}&$select=name,fields,semantic,vectorSearch"
            idx = self._run("search_definitions", ["az", "rest", "--method", "get", "--url", url, "--resource", "https://search.azure.com", "--query",
                                                   "value[].{name:name,fieldCount:length(fields),fieldTypes:fields[].type,vectorFields:length(fields[?dimensions]),semanticConfigurations:length(semantic.configurations||`[]`),vectorProfiles:vectorSearch.profiles[].name,vectorAlgorithms:vectorSearch.algorithms[].kind,vectorizers:vectorSearch.vectorizers[].kind}"], alias)
            if idx.outcome in ("ok", "empty"):
                props["index_definitions"] = sanitize.clean_value(idx.data or [], self.aliases)

        ev_id = f"EV-{alias}"
        self.resources.append({
            "alias": alias, "type": item.get("type") or "unknown", "kind": item.get("kind"), "location": item.get("location"),
            "environment": self.scope.environment, "resource_group_alias": rg_alias, "properties": props, "evidence_ids": [ev_id],
        })
        summary = ", ".join(f"{k}={json.dumps(v)}" for k, v in list(props.items())[:8] if not isinstance(v, (list, dict)))
        self.evidence.append(self._evidence(ev_id, "azure_resource_config", alias, item.get("type"), item.get("location"),
                                            f"Deployed configuration of {alias} ({item.get('type')}) in the {self.scope.environment} environment. "
                                            f"Selected properties: {summary or 'see azure-configuration.json'}.",
                                            "Property-selected projection only; data plane content was not read." if detail.outcome == "ok"
                                            else f"Configuration collection outcome: {detail.outcome}."))

    def _collect_rbac(self, rg_alias: str) -> None:
        res = self._run("rbac", ["az", "role", "assignment", "list", "--resource-group", self.scope.resource_group, *self._sub_args(),
                                 "--include-inherited", "--query", "[].{principalType:principalType,role:roleDefinitionName,scope:scope,principal:principalId}"], rg_alias)
        if res.outcome not in ("ok", "empty"):
            return
        rows = sanitize.clean_value(res.data or [], self.aliases)
        ev_id = f"EV-AZ-RBAC-{rg_alias.split('-')[-1]}"
        self.resources.append({"alias": f"AZ-RBAC-{rg_alias.split('-')[-1]}", "type": "Microsoft.Authorization/roleAssignments", "kind": None,
                               "location": None, "environment": self.scope.environment, "resource_group_alias": rg_alias,
                               "properties": {"assignments": rows}, "evidence_ids": [ev_id]})
        roles = sorted({f"{r.get('role')} ({r.get('principalType')})" for r in rows})
        self.evidence.append(self._evidence(ev_id, "azure_rbac", None, "Microsoft.Authorization/roleAssignments", None,
                                            f"{len(rows)} role assignments effective on {rg_alias} ({self.scope.environment}). Distinct role/principal types: {'; '.join(roles[:15])}.",
                                            "Principals aliased; group membership and PIM eligibility not resolved."))

    def _collect_policy(self, rg_alias: str) -> None:
        res = self._run("policy", ["az", "policy", "state", "summarize", "--resource-group", self.scope.resource_group, *self._sub_args(),
                                   "--query", "{nonCompliantResources:results.nonCompliantResources,nonCompliantPolicies:results.nonCompliantPolicies,assignments:policyAssignments[].{nonCompliantResources:results.nonCompliantResources,policyDefinitions:length(policyDefinitions||`[]`)}}"], rg_alias)
        if res.outcome != "ok":
            return
        data = sanitize.clean_value(res.data, self.aliases)
        ev_id = f"EV-AZ-POLICY-{rg_alias.split('-')[-1]}"
        self.resources.append({"alias": f"AZ-POLICY-{rg_alias.split('-')[-1]}", "type": "Microsoft.PolicyInsights/policyStates", "kind": None,
                               "location": None, "environment": self.scope.environment, "resource_group_alias": rg_alias,
                               "properties": data, "evidence_ids": [ev_id]})
        self.evidence.append(self._evidence(ev_id, "azure_policy", None, "Microsoft.PolicyInsights/policyStates", None,
                                            f"Azure Policy compliance summary for {rg_alias} ({self.scope.environment}): "
                                            f"{data.get('nonCompliantResources')} non-compliant resources across {data.get('nonCompliantPolicies')} policies.",
                                            "Summary only; individual policy definitions are not exported."))

    def _evidence(self, ev_id: str, source_type: str, alias: str | None, rtype: str | None, location: str | None, description: str, limitations: str) -> dict[str, Any]:
        return {
            "id": ev_id,
            "criteria": [],
            "source_type": source_type,
            "classification": "observed",
            "perspective": "deployed",
            "location": None,
            "repository_revision": None,
            "azure_resource": {"alias": alias, "type": rtype, "location": location} if alias else None,
            "environment": self.scope.environment,
            "description": description,
            "discovered_at": self.now,
            "command_template": self.attempts[-1]["command_template"] if self.attempts else None,
            "limitations": limitations,
        }


# --------------------------------------------------------------------------- telemetry

TELEMETRY_QUERIES: dict[str, str] = {
    "requests": "requests | summarize n=count(), failed=countif(success == false), p50=percentile(duration, 50), p95=percentile(duration, 95) by bin(timestamp, 1d) "
                "| summarize days=count(), total=sum(n), avg_daily=avg(n), max_daily=max(n), failure_rate=todouble(sum(failed))/todouble(sum(n)), p50_ms=avg(p50), p95_ms=max(p95)",
    "dependencies_by_type": "dependencies | summarize calls=count(), failed=countif(success == false), p95_ms=percentile(duration, 95) by type | top 20 by calls",
    "throttling": "dependencies | where resultCode == '429' | summarize n=count() by bin(timestamp, 1d) | summarize days_with_429=count(), total_429=sum(n)",
    "genai_usage": "dependencies | where isnotempty(customDimensions['gen_ai.usage.input_tokens']) or isnotempty(customDimensions['gen_ai.request.model']) "
                   "| extend model=tostring(customDimensions['gen_ai.request.model']), tin=toint(customDimensions['gen_ai.usage.input_tokens']), tout=toint(customDimensions['gen_ai.usage.output_tokens']) "
                   "| summarize calls=count(), input_tokens=sum(tin), output_tokens=sum(tout), p95_input=percentile(tin, 95), p95_output=percentile(tout, 95), p95_ms=percentile(duration, 95) by model",
    "exceptions_by_type": "exceptions | summarize n=count() by type | top 15 by n",
}


def _tables_to_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and "tables" in data:
        table = data["tables"][0] if data["tables"] else {"columns": [], "rows": []}
        cols = [c.get("name") for c in table.get("columns", [])]
        return [dict(zip(cols, row)) for row in table.get("rows", [])]
    if isinstance(data, list):
        return data
    return []


def collect_telemetry(out: Path, scope: Scope, app: str, days: int, runner: Runner, execute: bool) -> dict[str, Any]:
    aliases = sanitize.AliasMap(workspace.work_dir(out) / "alias-map.json")
    app_alias = aliases.known_names().get(app.lower()) or aliases.alias(f"name:{app}", "AZ-APPI")
    aliases.register_name(app, app_alias)
    results: dict[str, Any] = {}
    attempts: list[dict[str, Any]] = []
    for name, kql in TELEMETRY_QUERIES.items():
        argv = ["az", "monitor", "app-insights", "query", "--app", app, "--resource-group", scope.resource_group,
                "--subscription", scope.subscription, "--analytics-query", kql, "--offset", f"{days}d"]
        template = " ".join(argv).replace(app, app_alias).replace(scope.resource_group, "{resource_group}").replace(scope.subscription, "{subscription}")
        if not execute:
            attempts.append({"collector": f"telemetry:{name}", "target": app_alias, "command_template": template, "outcome": "empty", "detail": "dry run"})
            continue
        res = runner(argv)
        attempts.append({"collector": f"telemetry:{name}", "target": app_alias, "command_template": template, "outcome": res.outcome,
                         "detail": str(sanitize.clean_value(res.detail, aliases)) if res.detail else None})
        if res.outcome == "ok":
            results[name] = sanitize.clean_value(_tables_to_rows(res.data), aliases)
    aliases.save()
    return {"app_alias": app_alias, "days": days, "results": results, "attempts": attempts}


def telemetry_to_package(out: Path, scope: Scope, telemetry: dict[str, Any]) -> int:
    """Turn aggregated telemetry into measured workload characteristics + evidence."""
    out = Path(out)
    now = utc_now()
    app_alias, days = telemetry["app_alias"], telemetry["days"]
    new_ev: list[dict[str, Any]] = []
    new_wl: list[dict[str, Any]] = []
    env_tok = scope.environment[:4].upper()
    for name, rows in telemetry["results"].items():
        ev_id = f"EV-TEL-{env_tok}-{app_alias.upper()}-{name.upper().replace('_', '-')}"
        new_ev.append({
            "id": ev_id, "criteria": [], "source_type": "telemetry_aggregate", "classification": "observed", "perspective": "runtime",
            "location": None, "repository_revision": None, "azure_resource": {"alias": app_alias, "type": "Microsoft.Insights/components", "location": None},
            "environment": scope.environment,
            "description": f"Aggregated Application Insights telemetry ({name}) for {app_alias} over the last {days} days: {json.dumps(rows)[:600]}",
            "discovered_at": now, "command_template": f"az monitor app-insights query --app {app_alias} --analytics-query <{name} template> --offset {days}d",
            "limitations": "Aggregates only; no request content, prompts, responses or user identifiers were queried.",
        })
        if name == "requests" and rows:
            r = rows[0]
            for key, unit in (("avg_daily", "requests/day"), ("max_daily", "requests/day"), ("failure_rate", "ratio"), ("p95_ms", "ms")):
                if r.get(key) is not None:
                    new_wl.append({"id": f"WL-TEL-{env_tok}-{app_alias.upper()}-REQ-{key.upper().replace('_', '-')}", "name": f"Requests {key.replace('_', ' ')} ({app_alias})",
                                   "value": round(float(r[key]), 4), "unit": unit, "value_type": "measured", "period": f"last {days} days",
                                   "environment": scope.environment, "source": "Application Insights", "notes": None,
                                   "evidence_refs": [ev_id], "confidence": "high"})
    _merge(out / "evidence.json", "evidence", new_ev)
    _merge(out / "workload-characteristics.json", "characteristics", new_wl)
    manifest = load_json(out / "manifest.json")
    manifest["azure_scope"]["telemetry_authorised"] = True
    manifest["azure_scope"]["authorised"] = True
    manifest["azure_scope"]["authorised_by"] = manifest["azure_scope"].get("authorised_by") or scope.authorised_by
    if new_ev:
        if "azure_telemetry" not in manifest["discovery_modes"]:
            manifest["discovery_modes"].append("azure_telemetry")
        _add_env(manifest, scope.environment, "azure_telemetry")
    else:
        note = f"Application Insights telemetry for {app_alias} ({scope.environment}) returned no aggregates."
        if note not in manifest["evidence_sources_unavailable"]:
            manifest["evidence_sources_unavailable"].append(note)
    manifest["azure_scope"]["command_templates"] = sorted(set(manifest["azure_scope"].get("command_templates", []) + [a["command_template"] for a in telemetry["attempts"]]))
    manifest["azure_scope"]["failed_attempts"] = sorted(set(manifest["azure_scope"].get("failed_attempts", []) + [f"{a['collector']}: {a['outcome']}" for a in telemetry["attempts"] if a["outcome"] not in ("ok", "empty")]))
    dump_json(out / "manifest.json", manifest)
    return len(new_ev)


# --------------------------------------------------------------------------- package integration

def _merge(path: Path, key: str, new_items: list[dict[str, Any]], id_key: str = "id") -> None:
    doc = load_json(path)
    ids = {i[id_key] for i in new_items}
    doc[key] = [i for i in doc.get(key, []) if i.get(id_key) not in ids] + new_items
    dump_json(path, doc)


def _add_env(manifest: dict[str, Any], env: str, via: str) -> None:
    for e in manifest["environments_inspected"]:
        if e["name"] == env:
            if via not in e["inspected_via"]:
                e["inspected_via"].append(via)
            return
    manifest["environments_inspected"].append({"name": env, "inspected_via": [via], "notes": None})


def write_collection(out: Path, collector: Collector, summary: dict[str, Any]) -> None:
    out = Path(out)
    scope = collector.scope
    cfg = load_json(out / "azure-configuration.json")
    cfg["schema_version"] = SCHEMA_VERSION
    cfg["collections"] = [c for c in cfg.get("collections", []) if not (c["environment"] == scope.environment and c["resource_group_alias"] == summary["resource_group_alias"])]
    cfg["collections"].append({"environment": scope.environment, "subscription_alias": summary["subscription_alias"],
                               "resource_group_alias": summary["resource_group_alias"], "authorised_by": scope.authorised_by,
                               "collected_at": collector.now, "telemetry": False})
    new_aliases = {r["alias"] for r in collector.resources}
    cfg["resources"] = [r for r in cfg.get("resources", []) if r["alias"] not in new_aliases] + collector.resources
    cfg["attempts"] = cfg.get("attempts", []) + collector.attempts
    dump_json(out / "azure-configuration.json", cfg)
    _merge(out / "evidence.json", "evidence", collector.evidence)

    manifest = load_json(out / "manifest.json")
    pre = summary["preflight"]
    az = manifest["azure_scope"]
    az["cli_available"] = pre["cli_available"]
    az["authenticated"] = pre["authenticated"]
    az["command_templates"] = sorted(set(az.get("command_templates", []) + [a["command_template"] for a in collector.attempts]))
    az["failed_attempts"] = sorted(set(az.get("failed_attempts", []) + [f"{a['collector']} {a.get('target') or ''}: {a['outcome']}".replace("  ", " ") for a in collector.attempts if a["outcome"] not in ("ok", "empty")]))
    scopes = [s for s in az.get("scopes", []) if not (s.get("environment") == scope.environment and s.get("resource_group_alias") == summary["resource_group_alias"])]
    scopes.append({"environment": scope.environment, "subscription_alias": summary["subscription_alias"], "resource_group_alias": summary["resource_group_alias"]})
    az["scopes"] = scopes
    if collector.resources:
        az["authorised"] = True
        az["authorised_by"] = scope.authorised_by
        if "azure_configuration" not in manifest["discovery_modes"]:
            manifest["discovery_modes"].append("azure_configuration")
        _add_env(manifest, scope.environment, "azure_configuration")
    else:
        note = f"Azure configuration for {scope.environment} could not be collected ({pre['outcomes']})."
        if note not in manifest["evidence_sources_unavailable"]:
            manifest["evidence_sources_unavailable"].append(note)
    dump_json(out / "manifest.json", manifest)
