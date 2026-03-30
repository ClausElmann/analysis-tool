"""Domain asset matcher — maps assets to a domain using keyword and path heuristics.

Output is always:
* sorted (deterministic)
* deduplicated
* based only on the asset dict fields (id, path, content)
"""

from __future__ import annotations

import re
from typing import Dict, List

# ---------------------------------------------------------------------------
# Domain keyword registry
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "identity_access": [
        "identity", "auth", "login", "logout", "token", "jwt", "oauth",
        "permission", "role", "claim", "user", "password", "credential",
        "otp", "mfa", "sso", "openid", "saml", "scim", "2fa", "totp",
    ],
    "localization": [
        "localization", "localisation", "locale", "language", "translation",
        "resource", "string", "culture", "i18n", "l10n", "multilingual",
    ],
    "customer_management": [
        "customer", "account", "organisation", "organization", "company",
        "tenant", "client", "crm", "customer_setting", "api_key", "ftp",
        "saml", "logo",
    ],
    "customer_administration": [
        "customer", "account", "organisation", "organization", "company",
        "tenant", "profile", "address", "contact", "crm", "client",
    ],
    "profile_management": [
        "profile", "profile_role", "profile_user", "profile_level",
        "profileaccess", "profilerole", "userprofil",
    ],
    "address_management": [
        "address", "street", "geography", "geo", "municipality",
        "owner", "addressaccess", "dk", "no", "se", "fi", "lookup",
    ],
    "phone_numbers": [
        "phone", "phonenumber", "mobilenumber", "operator", "network",
        "provider", "import", "msisdn", "carrier", "prefix",
    ],
    "positive_list": [
        "positivelist", "positive_list", "supply_number", "levelcombination",
        "muncipality", "levelfilter", "level_combination",
    ],
    "lookup": [
        "lookup", "addresslookup", "ownerlookup", "prelookup", "coded_lookup",
        "document_lookup", "lookupresult", "lookuprequest",
    ],
    "templates": [
        "template", "messagetemplate", "mergefields", "merge_field",
        "templateversion", "sms_template", "email_template", "voice_template",
    ],
    "sms_group": [
        "smsgroup", "sms_group", "groupmessage", "smsstencil", "smsbatch",
        "smslog", "smsstatistic", "approval", "schedule",
    ],
    "delivery": [
        "delivery", "gatewayapi", "infobip", "sendgrid", "eboks",
        "voice_message", "web_message", "sms_gateway", "deliverystatus",
    ],
    "subscription": [
        "subscription", "subscribe", "unsubscribe", "supplysubscription",
        "selfenrollment", "subscriberlist", "subscriptionnotification",
    ],
    "enrollment": [
        "enrollment", "enrolment", "selfenrollment", "citizenenrollment",
        "enrollmentstep", "enrolladdress",
    ],
    "standard_receivers": [
        "standardreceiver", "standard_receiver", "receivergroup",
        "receiverkeyword", "inboundrouting", "scim",
    ],
    "conversation": [
        "conversation", "conversationphonenumber", "twoway", "two_way",
        "inbound_sms", "replysms", "conversationstatus",
    ],
    "benchmark": [
        "benchmark", "performance", "throughput", "latency", "load",
        "stress", "measure", "kpi", "sla", "infoportal", "kvhx",
    ],
    "webhook": [
        "webhook", "webhookdelivery", "webhookregistration", "webhookretry",
        "outboundwebhook", "callback",
    ],
    "web_messages": [
        "webmessage", "web_message", "webmessagemodule", "profilewebmessage",
    ],
    "voice": [
        "voice", "voicemessage", "virtualphone", "infobip_voice",
        "voicedelivery", "text_to_speech",
    ],
    "eboks_integration": [
        "eboks", "digitalpost", "eboksstatistic", "eboksexample",
        "digitalletter",
    ],
    "email": [
        "email", "emailmessage", "emailtemplate", "emailattachment",
        "sendgrid", "mailsend", "smtp",
    ],
    "data_import": [
        "dataimport", "data_import", "importmapping", "importrow",
        "importconfig", "importfile",
    ],
    "activity_log": [
        "activitylog", "activity_log", "audittrail", "audit_log",
        "useraudit", "systemaudit",
    ],
    "logging": [
        "log", "systemlog", "fatalerror", "requestlog", "querylog",
        "logentry", "logtable",
    ],
    "monitoring": [
        "monitor", "health", "alert", "heartbeat", "watchdog",
        "diagnostic", "uptime", "databasecheck", "versioncheck",
    ],
    "job_management": [
        "job", "backgroundjob", "jobschedule", "quartznet", "quartz",
        "scheduler", "jobtracking", "hangfire",
    ],
    "statistics": [
        "statistic", "statistics", "phonestatistic", "addressstatistic",
        "requeststatistic", "mapstatistic",
    ],
    "reporting": [
        "report", "analytic", "dashboard", "chart", "bisearch",
        "operationalreport", "pdf_capability", "summary",
    ],
    "finance": [
        "finance", "economic", "invoice", "billing", "balance",
        "budget", "economicinvoice", "payment",
    ],
    "pipeline_crm": [
        "pipeline", "crm", "prospect", "salesforce", "opportunity",
        "deal", "sales_history",
    ],
    "pipeline_sales": [
        "sales", "pipeline", "lead", "deal", "opportunity",
        "funnel", "stage", "prospect", "conversion",
    ],
    "integrations": [
        "integration", "api", "webhook", "endpoint", "connector",
        "sync", "bridge", "adapter", "provider", "gateway", "http",
    ],
    "messaging": [
        "message", "sms", "email", "notification", "send", "deliver",
        "template", "channel", "inbox", "outbox", "recipient", "text",
        "push", "mms",
    ],
    "recipient_management": [
        "recipient", "subscriber", "contact", "distribution", "list",
        "group", "segment", "target", "import", "export",
    ],
    "subscriptions": [
        "subscription", "subscribe", "unsubscribe", "plan", "billing",
        "invoice", "payment", "renew", "trial", "tier", "licence", "license",
    ],
}

# Precompiled word-boundary patterns (keyword → pattern)
_COMPILED: Dict[str, Dict[str, re.Pattern]] = {}


def _get_patterns(domain_name: str) -> Dict[str, re.Pattern]:
    if domain_name not in _COMPILED:
        keywords = _DOMAIN_KEYWORDS.get(domain_name, [domain_name.replace("_", " ")])
        _COMPILED[domain_name] = {
            kw: re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            for kw in keywords
        }
    return _COMPILED[domain_name]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _asset_text(asset: Dict) -> str:
    """Return combined, lowercased searchable text from an asset dict."""
    return " ".join(
        str(asset.get(f, "") or "")
        for f in ("id", "path", "content")
    ).lower()


def _name_variants(domain_name: str) -> List[str]:
    """Return all lowercase substrings of the domain name (word parts)."""
    return [v for v in domain_name.lower().split("_") if v]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def match_assets(domain_name: str, assets: List[Dict]) -> List[str]:
    """Return sorted, deduplicated asset IDs that match *domain_name*.

    Matching strategy (an asset matches if ANY rule fires):
    1. Any name-variant of the domain name appears in id or path.
    2. At least one keyword from the domain keyword list appears as a whole
       word in ``id + path + content``.
    """
    patterns = _get_patterns(domain_name)
    variants = _name_variants(domain_name)

    matched: set = set()
    for asset in assets:
        asset_id = asset.get("id", "")
        text = _asset_text(asset)

        # Rule 1 — domain name fragment in id/path
        id_path = (str(asset.get("id", "")) + " " + str(asset.get("path", ""))).lower()
        if any(v in id_path for v in variants):
            matched.add(asset_id)
            continue

        # Rule 2 — keyword word-boundary match anywhere in the asset
        if any(pat.search(text) for pat in patterns.values()):
            matched.add(asset_id)

    return sorted(matched)
