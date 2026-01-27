import os
import unittest
from pathlib import Path
from unittest.mock import patch
from tempfile import TemporaryDirectory


class TestPaths(unittest.TestCase):
    def setUp(self):
        self._env_snapshot = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_snapshot)

    def test_resolve_paths_returns_correct_structure(self):
        from app.utils.paths import resolve_paths, WorkspacePaths

        paths = resolve_paths()

        self.assertIsInstance(paths, WorkspacePaths)
        self.assertTrue(paths.root_app_path.exists())
        self.assertTrue(paths.app_path.exists())


if __name__ == "__main__":
    unittest.main()