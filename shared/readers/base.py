"""The 'pluggable reader' layer (your "make it a skill" idea).

Today we only read PDFs. If a bank later sends Excel or CSV, you add ONE new
file here (e.g. excel_reader.py) that follows this same interface, and the rest
of the system doesn't change. No rewrite needed.

A reader's job is only to turn a file into a list of positioned text items.
Understanding what those items MEAN (which number is Gross NAV) is the bank
parser's job, not the reader's.
"""
from abc import ABC, abstractmethod
from typing import Dict, List


class StatementReader(ABC):
    @abstractmethod
    def extract_text_items(self, path) -> List[Dict]:
        """Return text pieces with their position, as a list of dicts:
        {"text": str, "page": int, "x0": float, "y0": float, "x1": float, "y1": float}
        Coordinates are in PDF points (72 per inch), origin top-left.
        """
        raise NotImplementedError

    @abstractmethod
    def full_text(self, path) -> str:
        """Return the whole document as plain text (handy for finding client names)."""
        raise NotImplementedError
