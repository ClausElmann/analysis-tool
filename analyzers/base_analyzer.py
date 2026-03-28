"""Base analyzer contract."""


class BaseAnalyzer:
    def analyze(self, file_path: str, content: str, analysis):
        raise NotImplementedError
