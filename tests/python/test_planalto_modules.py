"""The current extractor must not load the legacy preparation workflow."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PlanaltoModules(unittest.TestCase):
    def test_current_extractor_is_independent_of_legacy_preparation(self):
        result = subprocess.run(
            [sys.executable, '-B', '-c',
             "import sys; sys.path.insert(0, 'scripts'); "
             "import extract_struck_html; "
             "assert 'extract_previous_html' not in sys.modules; "
             "assert 'check_official_sources' not in sys.modules; "
             "assert 'import_official' not in sys.modules; "
             "assert 'official_http' not in sys.modules; "
             "from planalto_html import EvidenceHTML; "
             "assert issubclass(extract_struck_html.StruckHTML, EvidenceHTML)"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_monitor_keeps_parser_compatibility(self):
        import official_html
        import check_official_sources
        import import_official
        self.assertIs(check_official_sources.OfficialHTML, official_html.OfficialHTML)
        self.assertIs(check_official_sources.parse_html, official_html.parse_html)
        self.assertIs(import_official.ARTICLE, official_html.ARTICLE_IDENTIFIER)
