"""
domain_builder.py — Groups slice outputs into domain clusters.

Reads existing deterministic slice outputs from data/ and builds an initial
domain map WITHOUT calling AI. The result can then be refined by the
Refiner stage.

Input slice files used:
  api_db_map.json       → controller → domain via naming heuristics
  batch_jobs.json       → job category → domain
  event_map.json        → event name prefix → domain
  webhook_map.json      → source system → domain
  integrations.json     → interface name prefix → domain
  background_services.json → service name → domain

Output:
  domains/{domain_name}/000_meta.json
  domains/{domain_name}/010_entities.json
  ...

Domain grouping strategy (deterministic, no AI):
  1. Normalize name: strip common suffixes (Controller, Service, Repository…)
  2. Extract domain token: first CamelCase word of the normalized name
  3. Assign to domain bucket
  4. Fallback: "Core" bucket

Quality scoring is computed from coverage metrics (no AI required).
"""

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from core.ai_processor import DOMAIN_OUTPUT_KEYS

# ── Name normalisation ────────────────────────────────────────────────────────

_STRIP_SUFFIXES = re.compile(
    r"(Controller|Service|Repository|Repo|Handler|Manager|"
    r"Worker|Processor|Job|Action|Query|Command|Notification|"
    r"Event|Factory|Builder|Provider|Mapper|Validator|"
    r"Module|Component|Client|Facade|Adapter|Listener)$"
)

_CAMEL_SPLIT = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _domain_token(name: str) -> str:
    """Extract the primary domain token from a CamelCase name."""
    # Remove known suffixes
    clean = _STRIP_SUFFIXES.sub("", name)
    # Split on camel-case boundaries
    parts = _CAMEL_SPLIT.split(clean)
    # First meaningful word is the domain token
    token = parts[0] if parts else clean
    return token or "Core"


# ── Domain cluster dataclass ──────────────────────────────────────────────────

@dataclass
class DomainCluster:
    name: str
    apis: list = field(default_factory=list)
    batch_jobs: list = field(default_factory=list)
    events: list = field(default_factory=list)
    webhooks: list = field(default_factory=list)
    integrations: list = field(default_factory=list)
    background_services: list = field(default_factory=list)

    # Quality metrics
    @property
    def coverage(self) -> dict:
        return {
            "api_endpoints": len(self.apis),
            "batch_jobs": len(self.batch_jobs),
            "events": len(self.events),
            "webhooks": len(self.webhooks),
            "integrations": len(self.integrations),
            "background_services": len(self.background_services),
        }

    @property
    def confidence(self) -> float:
        """Heuristic confidence based on coverage breadth (0.0–1.0)."""
        filled = sum(1 for v in self.coverage.values() if v > 0)
        return round(min(filled / 6, 1.0), 2)

    @property
    def complexity_score(self) -> int:
        """1–10 complexity estimate based on total item count."""
        total = sum(self.coverage.values())
        return max(1, min(10, total // 5 + 1))

    @property
    def roi_score(self) -> int:
        """1–10 rebuild ROI estimate — higher for well-connected domains."""
        filled = sum(1 for v in self.coverage.values() if v > 0)
        return max(1, min(10, filled * 2))


# ── DomainBuilder ─────────────────────────────────────────────────────────────

class DomainBuilder:
    """
    Builds domain clusters from existing slice outputs (deterministic).

    Args:
        data_root:    Path to data/ directory (slice JSON files)
        domains_root: Output path for domain/ directory tree
    """

    def __init__(self, data_root: str, domains_root: str):
        self._data = Path(data_root)
        self._domains_root = Path(domains_root)

    # ── Loading helpers ───────────────────────────────────────────────────────

    def _load(self, filename: str) -> dict | list:
        path = self._data / filename
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # ── Grouping passes ───────────────────────────────────────────────────────

    def _group_apis(self, clusters: dict):
        data = self._load("api_db_map.json")
        for item in data.get("mappings", []):
            token = _domain_token(item.get("controller", "Core"))
            clusters[token].apis.append({
                "controller": item.get("controller"),
                "method": item.get("controller_method"),
                "url": item.get("api_url"),
            })

    def _group_batch_jobs(self, clusters: dict):
        data = self._load("batch_jobs.json")
        for item in data.get("jobs", []):
            # Use category as primary domain signal
            cat = item.get("category", "")
            token = _domain_token(cat.replace("_", " ").title().replace(" ", "")) if cat else "Core"
            clusters[token].batch_jobs.append({
                "job": item.get("job"),
                "category": item.get("category"),
            })

    def _group_events(self, clusters: dict):
        data = self._load("event_map.json")
        for item in data.get("events", []):
            token = _domain_token(item.get("event", "Core"))
            clusters[token].events.append({
                "event": item.get("event"),
                "publishers": item.get("publishers", []),
                "handlers": item.get("handlers", []),
            })

    def _group_webhooks(self, clusters: dict):
        data = self._load("webhook_map.json")
        for item in data.get("webhooks", []):
            # Webhooks group by source system
            source = item.get("source", "Core").replace(" ", "")
            clusters[source].webhooks.append({
                "controller": item.get("controller"),
                "source": item.get("source"),
            })

    def _group_integrations(self, clusters: dict):
        data = self._load("integrations.json")
        for item in data.get("integrations", []):
            token = _domain_token(item.get("interface", "Core"))
            clusters[token].integrations.append({
                "interface": item.get("interface"),
                "implementation": item.get("implementation"),
                "host_project": item.get("host_project"),
            })

    def _group_background_services(self, clusters: dict):
        data = self._load("background_services.json")
        for item in data.get("services", []):
            token = _domain_token(item.get("name", "Core"))
            clusters[token].background_services.append({
                "name": item.get("name"),
                "type": item.get("type"),
                "host": item.get("host"),
            })

    # ── Build ────────────────────────────────────────────────────────────────

    def build(self) -> dict[str, DomainCluster]:
        """
        Run all grouping passes and return the domain cluster map.

        Returns:
            dict mapping domain_name → DomainCluster
        """
        clusters: dict[str, DomainCluster] = defaultdict(lambda: DomainCluster(name=""))
        self._group_apis(clusters)
        self._group_batch_jobs(clusters)
        self._group_events(clusters)
        self._group_webhooks(clusters)
        self._group_integrations(clusters)
        self._group_background_services(clusters)
        # Assign names
        for name, cluster in clusters.items():
            cluster.name = name
        return dict(clusters)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _write_json(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    def write(self, clusters: dict[str, DomainCluster]):
        """
        Write domain cluster files to domains/{name}/*.json.

        File naming follows the spec:
          000_meta.json, 010_entities.json … 090_rebuild.json
        """
        for name, cluster in sorted(clusters.items()):
            domain_dir = self._domains_root / name

            # 000_meta.json
            self._write_json(domain_dir / "000_meta.json", {
                "domain": name,
                "confidence": cluster.confidence,
                "coverage": cluster.coverage,
                "complexity_score": cluster.complexity_score,
                "roi_score": cluster.roi_score,
            })

            # 010_entities.json — populated by AI stages later
            self._write_json(domain_dir / "010_entities.json", {"domain": name, "entities": []})

            # 020_behaviors.json
            self._write_json(domain_dir / "020_behaviors.json", {"domain": name, "behaviors": []})

            # 030_flows.json
            self._write_json(domain_dir / "030_flows.json", {"domain": name, "flows": []})

            # 040_events.json — pre-populated from slice
            self._write_json(domain_dir / "040_events.json", {
                "domain": name,
                "events": cluster.events,
            })

            # 050_batch.json — pre-populated from slice
            self._write_json(domain_dir / "050_batch.json", {
                "domain": name,
                "batch_jobs": cluster.batch_jobs,
            })

            # 060_integrations.json — pre-populated from slice
            self._write_json(domain_dir / "060_integrations.json", {
                "domain": name,
                "integrations": cluster.integrations,
                "webhooks": cluster.webhooks,
                "background_services": cluster.background_services,
            })

            # 070_rules.json
            self._write_json(domain_dir / "070_rules.json", {"domain": name, "rules": []})

            # 080_pseudocode.json
            self._write_json(domain_dir / "080_pseudocode.json", {"domain": name, "pseudocode": []})

            # 090_rebuild.json
            self._write_json(domain_dir / "090_rebuild.json", {
                "domain": name,
                "rebuild_requirements": [],
            })

    def build_and_write(self) -> dict[str, DomainCluster]:
        """Convenience: build clusters and write to disk in one call."""
        clusters = self.build()
        self.write(clusters)
        return clusters
