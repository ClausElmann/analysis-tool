"""JSON output writer."""

import json
import os


class JsonWriter:
    def __init__(self, output_root: str = "output-data") -> None:
        self.output_root = output_root

    def write(self, analyses) -> None:
        os.makedirs(self.output_root, exist_ok=True)
        payload = [analysis.to_dict() for analysis in analyses]
        with open(os.path.join(self.output_root, "analysis-index.json"), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
