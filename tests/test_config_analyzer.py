"""Tests for ConfigAnalyzer."""

import pytest

from analyzers.config_analyzer import ConfigAnalyzer
from core.model import FileAnalysis


def make_analysis(path="appsettings.json"):
    return FileAnalysis(project="test", path=path, type="config", technology="config")


def make_analyzer():
    return ConfigAnalyzer()


# 1. Valid JSON-style config with connections and URLs
def test_config_valid_json_config():
    content = """{
  "ConnectionStrings": {
    "DefaultConnection": "Server=myserver;Database=mydb;"
  },
  "ApiEndpoint": "https://api.example.com/v1",
  "LogLevel": "Information",
  "FeatureFlags": {
    "EnableCache": true
  }
}
"""
    analyzer = make_analyzer()
    analysis = make_analysis("appsettings.json")
    analyzer.analyze("appsettings.json", content, analysis)

    assert analysis.summary != ""
    assert "keys" in analysis.key_elements
    assert isinstance(analysis.key_elements["keys"], list)
    assert len(analysis.key_elements["keys"]) > 0
    assert isinstance(analysis.domain_signals.get("integration_hints", []), list)
    assert isinstance(analysis.dependencies.get("urls", []), list)
    assert "https://api.example.com/v1" in analysis.dependencies["urls"]


# 2. Partial config with only YAML-style keys (no URLs)
def test_config_yaml_style_keys():
    content = """
database:
  host: localhost
  port: 5432
  name: mydb

logging:
  level: debug
  output: console
"""
    analyzer = make_analyzer()
    analysis = make_analysis("config.yaml")
    analyzer.analyze("config.yaml", content, analysis)

    assert "keys" in analysis.key_elements
    assert isinstance(analysis.key_elements["keys"], list)
    assert len(analysis.key_elements["keys"]) > 0
    assert isinstance(analysis.dependencies.get("urls", []), list)
    assert isinstance(analysis.risks_notes, list)


# 3. Empty / no signals
def test_config_empty_content():
    content = ""
    analyzer = make_analyzer()
    analysis = make_analysis("empty.json")
    analyzer.analyze("empty.json", content, analysis)

    assert analysis.summary != ""
    assert isinstance(analysis.key_elements.get("keys", []), list)
    assert isinstance(analysis.domain_signals.get("integration_hints", []), list)
    assert isinstance(analysis.dependencies.get("urls", []), list)
    assert analysis.raw_extract is not None


# 4. Edge case: config with multiple URLs and connection hints
def test_config_multiple_urls_and_hints():
    content = """{
  "ServiceEndpoint": "https://service.example.com",
  "CallbackUrl": "https://callback.example.com/hook",
  "ConnectionString": "Server=db.example.com;Port=1433;",
  "Timeout": 30,
  "RetryCount": 3
}
"""
    analyzer = make_analyzer()
    analysis = make_analysis("service-config.json")
    analyzer.analyze("service-config.json", content, analysis)

    assert "keys" in analysis.key_elements
    assert isinstance(analysis.key_elements["keys"], list)
    assert isinstance(analysis.domain_signals["integration_hints"], list)
    assert len(analysis.domain_signals["integration_hints"]) > 0
    assert isinstance(analysis.dependencies["urls"], list)
    assert len(analysis.dependencies["urls"]) >= 2
    assert analysis.raw_extract is not None
