"""Pipeline orchestration for the analysis engine.

Flow:
1. Classify each file.
2. Create a normalized FileAnalysis object.
3. Read content safely.
4. Route the file to a matching analyzer.
5. Return a uniform list of results for reporting.
"""

from analyzers.angular_analyzer import AngularAnalyzer
from analyzers.batch_analyzer import BatchAnalyzer
from analyzers.config_analyzer import ConfigAnalyzer
from analyzers.csharp_analyzer import CSharpAnalyzer
from analyzers.sql_analyzer import SqlAnalyzer
from core.file_classifier import FileClassifier
from core.model import FileAnalysis
from utils.file_utils import detect_project_name


class Pipeline:
    def __init__(self, root_path: str) -> None:
        self.root_path = root_path
        self.classifier = FileClassifier()
        self.csharp_analyzer = CSharpAnalyzer()
        self.sql_analyzer = SqlAnalyzer()
        self.angular_analyzer = AngularAnalyzer()
        self.config_analyzer = ConfigAnalyzer()
        self.batch_analyzer = BatchAnalyzer()

    def run(self, files):
        results = []
        for file_path in files:
            analysis = FileAnalysis()
            analysis.path = file_path
            analysis.project = detect_project_name(file_path, self.root_path)
            analysis.type = self.classifier.classify(file_path)
            analysis.technology = self.classifier.technology_for_type(analysis.type)
            content = self._read_file(file_path)
            if content is None:
                analysis.summary = "File could not be read safely."
                analysis.risks_notes.append("Unreadable file")
                results.append(analysis)
                continue

            if analysis.type == "csharp":
                self.csharp_analyzer.analyze(file_path, content, analysis)
            elif analysis.type == "sql":
                self.sql_analyzer.analyze(file_path, content, analysis)
            elif analysis.type == "angular":
                self.angular_analyzer.analyze(file_path, content, analysis)
            elif analysis.type == "config":
                self.config_analyzer.analyze(file_path, content, analysis)
            elif analysis.type == "batch":
                self.batch_analyzer.analyze(file_path, content, analysis)
            else:
                analysis.summary = "No specialized analyzer assigned."
                analysis.raw_extract = content[:1000]

            results.append(analysis)
        return results

    def _read_file(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                return handle.read()
        except OSError:
            return None
