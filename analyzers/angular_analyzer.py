"""Angular signal extraction analyzer.

This analyzer extracts lightweight signals from Angular-related files such as
components, services, routes, selectors, templates, and HTTP calls.
"""

import os
import re

from analyzers.base_analyzer import BaseAnalyzer


class AngularAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str, content: str, analysis):
        file_name = os.path.basename(file_path).lower()
        classes = re.findall(r"\bexport\s+class\s+(\w+)", content)
        selectors = re.findall(r'''selector\s*:\s*["']([^"']+)["']''', content)
        templates = re.findall(r'''templateUrl\s*:\s*["']([^"']+)["']''', content)
        routes = re.findall(r'''path\s*:\s*["']([^"']+)["']''', content)
        http_calls = re.findall(r"\.\s*(get|post|put|delete|patch)\s*\(", content, re.IGNORECASE)
        forms = re.findall(r"\b(FormGroup|FormControl|Validators)\b", content)

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
        analysis.key_elements["template_urls"] = sorted(set(templates))
        analysis.key_elements["routes"] = sorted(set(routes))
        analysis.key_elements["http_calls"] = [call.lower() for call in http_calls]
        analysis.domain_signals["roles"] = roles
        analysis.domain_signals["forms"] = sorted(set(forms))
        analysis.dependencies["ui_assets"] = sorted(set(templates))
        analysis.inputs_outputs["api_operations"] = [call.lower() for call in http_calls]
        analysis.raw_extract = content[:1000]
