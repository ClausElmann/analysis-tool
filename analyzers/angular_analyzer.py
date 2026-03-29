"""Angular signal extraction analyzer.

This analyzer extracts lightweight signals from Angular-related files such as
components, services, routes, selectors, templates, and HTTP calls.
"""

import os
import re

from analyzers.base_analyzer import BaseAnalyzer


class AngularAnalyzer(BaseAnalyzer):
    # Patterns to detect tab labels from common Angular tab components.
    # Captures: mat-tab[label="..."], p-tabPanel[header="..."], tab array
    # labels like { label: 'Overview' }.
    _TAB_PATTERNS = [
        re.compile(r'''<mat-tab\s[^>]*label=["']([^"']+)["']''', re.IGNORECASE),
        re.compile(r'''<p-tabPanel\s[^>]*header=["']([^"']+)["']''', re.IGNORECASE),
        re.compile(r'''label\s*:\s*["']([^"']+)["']''', re.IGNORECASE),
    ]

    def analyze(self, file_path: str, content: str, analysis):
        file_name = os.path.basename(file_path).lower()
        classes = re.findall(r"\bexport\s+class\s+(\w+)", content)
        selectors = re.findall(r'''selector\s*:\s*["']([^"']+)["']''', content)
        templates = re.findall(r'''templateUrl\s*:\s*["']([^"']+)["']''', content)
        routes = re.findall(r'''path\s*:\s*["']([^"']+)["']''', content)
        http_calls = re.findall(r"\.\s*(get|post|put|delete|patch)\s*\(", content, re.IGNORECASE)
        forms = re.findall(r"\b(FormGroup|FormControl|Validators)\b", content)
        tabs = self._extract_tabs(content)

        roles = []
        if ".component." in file_name:
            roles.append("component")
        if ".service." in file_name:
            roles.append("service")
        if ".module." in file_name:
            roles.append("module")
        if ".routing." in file_name or "routes" in file_name:
            roles.append("routing")

        analysis.summary = "Angular-related file analyzed for UI and API signals."
        analysis.key_elements["classes"] = sorted(set(classes))
        analysis.key_elements["selectors"] = sorted(set(selectors))
        analysis.key_elements["tabs"] = tabs
        analysis.key_elements["template_urls"] = sorted(set(templates))
        analysis.key_elements["routes"] = sorted(set(routes))
        analysis.key_elements["http_calls"] = [call.lower() for call in http_calls]
        analysis.domain_signals["roles"] = roles
        analysis.domain_signals["forms"] = sorted(set(forms))
        analysis.dependencies["ui_assets"] = sorted(set(templates))
        analysis.inputs_outputs["api_operations"] = [call.lower() for call in http_calls]
        analysis.raw_extract = content[:1000]

    def _extract_tabs(self, content: str) -> list:
        """Extract tab labels from mat-tab, p-tabPanel, and tab array definitions.

        Only labels explicitly declared in the source are returned. Labels are
        returned in source order and deduplicated while preserving first-seen order.
        """
        seen: dict = {}
        for pattern in self._TAB_PATTERNS:
            for label in pattern.findall(content):
                clean = label.strip()
                if clean and clean not in seen:
                    seen[clean] = None
        return list(seen.keys())
