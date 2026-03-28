"""C# signal extraction analyzer.

This analyzer extracts lightweight structural signals from C# source files.
It is not a full parser and does not guarantee semantic correctness.
It is designed for large-solution inventory work where speed and broad coverage
matter more than perfect understanding of every file.
"""

import re

from analyzers.base_analyzer import BaseAnalyzer


class CSharpAnalyzer(BaseAnalyzer):
    def analyze(self, file_path: str, content: str, analysis):
        classes = re.findall(r"\bclass\s+(\w+)", content)
        interfaces = re.findall(r"\binterface\s+(\w+)", content)
        method_pattern = re.compile(
            r"\b(?:public|private|protected|internal)\s+(?:async\s+)?[\w<>,\[\]?]+\s+(\w+)\s*\(",
            re.MULTILINE,
        )
        methods = method_pattern.findall(content)
        endpoint_pattern = re.compile(r"\[(HttpGet|HttpPost|HttpPut|HttpDelete|Route)\b[^\]]*\]", re.MULTILINE)
        endpoints = endpoint_pattern.findall(content)

        keywords = []
        for keyword in ["status", "type", "code", "id", "date"]:
            if re.search(rf"\b{keyword}\b", content, re.IGNORECASE):
                keywords.append(keyword)

        namespaces = re.findall(r"^\s*using\s+([\w\.]+)\s*;", content, re.MULTILINE)
        injected_dependencies = re.findall(r"private\s+readonly\s+[\w<>,\.\[\]?]+\s+_(\w+)\s*;", content)

        analysis.summary = "C# file analyzed for structural signals."
        analysis.key_elements["classes"] = sorted(set(classes))
        analysis.key_elements["interfaces"] = sorted(set(interfaces))
        analysis.key_elements["methods"] = sorted(set(methods))
        analysis.key_elements["endpoints"] = endpoints
        analysis.domain_signals["keywords"] = keywords
        analysis.dependencies["namespaces"] = sorted(set(namespaces))
        analysis.dependencies["injected_fields"] = sorted(set(injected_dependencies))
        analysis.inputs_outputs["possible_http_attributes"] = endpoints
        analysis.raw_extract = content[:1000]

        if not classes and not interfaces and not methods:
            analysis.risks_notes.append("Low structural signal density in C# file")
