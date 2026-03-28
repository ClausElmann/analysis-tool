"""Tests for BatchAnalyzer."""

import pytest

from analyzers.batch_analyzer import BatchAnalyzer
from core.model import FileAnalysis


def make_analysis(path="sync_job.py"):
    return FileAnalysis(project="test", path=path, type="batch", technology="python")


def make_analyzer():
    return BatchAnalyzer()


# 1. Valid batch file with job names and schedule expressions
def test_batch_valid_job_and_cron():
    content = """
class OrderSyncJob:
    schedule = "0 */6 * * *"

    def execute(self):
        self.run()
        self.retry()

class DataLoader:
    schedule = "30 2 * * 1"

    def start(self):
        pass
"""
    analyzer = make_analyzer()
    analysis = make_analysis("jobs.py")
    analyzer.analyze("jobs.py", content, analysis)

    assert analysis.summary != ""
    assert "job_names" in analysis.key_elements
    assert isinstance(analysis.key_elements["job_names"], list)
    assert len(analysis.key_elements["job_names"]) > 0
    assert "schedule_expressions" in analysis.key_elements
    assert isinstance(analysis.key_elements["schedule_expressions"], list)
    assert isinstance(analysis.domain_signals.get("commands", []), list)
    assert isinstance(analysis.risks_notes, list)


# 2. Partial / no job patterns (only commands)
def test_batch_partial_only_commands():
    content = """
def process():
    start()
    execute()
    stop()
    resume()
"""
    analyzer = make_analyzer()
    analysis = make_analysis("process.py")
    analyzer.analyze("process.py", content, analysis)

    assert "job_names" in analysis.key_elements
    assert isinstance(analysis.key_elements["job_names"], list)
    assert "commands" in analysis.domain_signals
    assert isinstance(analysis.domain_signals["commands"], list)
    assert len(analysis.domain_signals["commands"]) > 0
    assert len(analysis.risks_notes) > 0


# 3. Empty / no signals
def test_batch_empty_content():
    content = ""
    analyzer = make_analyzer()
    analysis = make_analysis("empty.py")
    analyzer.analyze("empty.py", content, analysis)

    assert analysis.summary != ""
    assert isinstance(analysis.key_elements.get("job_names", []), list)
    assert isinstance(analysis.key_elements.get("schedule_expressions", []), list)
    assert isinstance(analysis.domain_signals.get("commands", []), list)
    assert isinstance(analysis.risks_notes, list)
    assert len(analysis.risks_notes) > 0
    assert analysis.raw_extract is not None


# 4. Edge case: Scheduler class with multiple workers and complex cron
def test_batch_scheduler_multiple_workers():
    content = """
class NightlyWorker:
    cron = "0 0 * * *"

    def run(self):
        pass

class WeeklyScheduler:
    cron = "0 8 * * 1"

    def execute(self):
        pass

class RetryTask:
    def retry(self):
        pass
"""
    analyzer = make_analyzer()
    analysis = make_analysis("workers.py")
    analyzer.analyze("workers.py", content, analysis)

    assert "job_names" in analysis.key_elements
    assert isinstance(analysis.key_elements["job_names"], list)
    assert len(analysis.key_elements["job_names"]) >= 2
    assert isinstance(analysis.key_elements.get("schedule_expressions", []), list)
    assert isinstance(analysis.domain_signals.get("commands", []), list)
    assert analysis.raw_extract is not None
