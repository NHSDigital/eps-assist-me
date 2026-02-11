import json
from pathlib import Path
from app.core.config import (
    get_logger,
)

logger = get_logger()


class SampleQuestionBank:
    """A collection of sample questions for testing purposes."""

    def __init__(self):
        self.questions = []

        project_root = Path(__file__).resolve().parents[2]
        path = project_root / "manifest.json"

        self._load_questions(path)

    def _load_questions(self, path):
        """Reads data from the manifest and populates the question list."""
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found! Expected it at: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.questions = [(q.get("id"), q.get("text"), q.get("tags", [])) for q in data.get("questions", [])]

    def filter_by_tags(self, tags: list[str]) -> list[tuple[int, str, list[dict[str, str]]]]:
        """Returns questions that match any of the provided tags."""
        if not tags:
            # If no tags provided, return all prompt-engineering questions by default
            tags = ["engineering"]

        filtered = []
        for q in self.questions:
            q_tags = q[2]
            q_tags = [q_tag["tag"] for q_tag in q_tags]
            if any(tag in q_tags for tag in tags):
                filtered.append(q)

        return filtered

    def get_questions(self, start, end, tags=None) -> list[tuple[int, str]]:
        """
        Pulls a selection of questions
        """
        default_info = "must be positive whole number"

        # Must be integers
        if not isinstance(start, int):
            raise TypeError(f"'start' {default_info}, got {type(start).__name__}")

        if not isinstance(end, int):
            raise TypeError(f"'end' {default_info}, got {type(end).__name__}")

        # Must be in valid range
        if start < 0:
            raise ValueError(f"'start' {default_info}")

        if end < 0 or end < start:
            raise ValueError(f"'end' {default_info} greater than or equal to 'start'")

        filtered = self.filter_by_tags(tags=tags)

        if start >= len(filtered):
            raise ValueError(f"'start' {default_info} less than total questions available ({len(filtered)})")

        if end > len(filtered):
            end = len(filtered) - 1
            logger.warning(f"'end' {default_info} less than {len(filtered) + 1}. Returning all available questions.")

        # Extract only the text (index 1) from the tuple
        return filtered[start : end + 1]

    def add_questions(self, question_text: str):
        self.questions.append((len(self.questions), question_text))

    def length(self) -> int:
        """
        Gets number of questions
        """
        return len(self.questions)
