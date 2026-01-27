# tests/test_loader.py

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from app.utils.loader import load_config, AgentConfig, SocketConfig, Config  # noqa: E402

class TestLoader(unittest.TestCase):
    def test_load_config_happy_path(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "app" / "config" / "prod"
            config_dir.mkdir(parents=True, exist_ok=True)

            (config_dir / "options.yml").write_text(
                "dataTypes:\n"
                "  - a\n"
                "  - b\n"
                "databaseTypes:\n"
                "  - mongo\n"
                "dataPlatformTypes:\n"
                "  - atlas\n"
                "eventStages:\n"
                "  - created\n"
                "  - paid\n"
            )
            (config_dir / "agent.yml").write_text(
                "data-ingestion: null\n"
                "data-cleaning: pipeline.yml\n"
                "data-analytics: null\n"
                "data-quality: null"
            )
            (config_dir / "streamTemplate.txt").write_text("Hello {event}")

            paths = SimpleNamespace(
                root_app_path=root,
                app_path=root / "app",
                config_path=config_dir,
                src_path=root / "app" / "src",
                api_path=root / "app" / "api",
                utils_path=root / "app" / "utils",
                static_path=root / "app" / "static",
            )

            ws = load_config(
                paths,
                debug_mode=False,
                app_path="app.main:app",
                app_port=8005,
                app_host="0.0.0.0",
            )

            self.assertIsInstance(ws, Config)
            self.assertIsInstance(ws.agent, AgentConfig)
            self.assertIsInstance(ws.socket, SocketConfig)

            self.assertEqual(ws.socket.dataTypes, ["a", "b"])
            self.assertEqual(ws.socket.databaseTypes, ["mongo"])
            self.assertEqual(ws.socket.dataPlatformTypes, ["atlas"])
            self.assertEqual(ws.socket.eventStages, ["created", "paid"])
            self.assertEqual(ws.socket.eventResponseTemplate, "Hello {event}")

    def test_load_config_missing_files_raises(self):
        """ Test for when prod config folder is missing required files. """

        with TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "app" / "config" / "prod"
            config_dir.mkdir(parents=True, exist_ok=True)

            paths = SimpleNamespace(
                root_app_path=root,
                app_path=root / "app",
                config_path=config_dir,
                src_path=root / "app" / "src",
                api_path=root / "app" / "api",
                utils_path=root / "app" / "utils",
                static_path=root / "app" / "static",
            )

            with self.assertRaises(FileNotFoundError):
                load_config(
                    paths,
                    debug_mode=False,
                    app_path="app.main:app",
                    app_port=8005,
                    app_host="0.0.0.0",
                )

    def test_load_config_non_list_yaml_values_become_empty_lists(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "app" / "config" / "prod"
            config_dir.mkdir(parents=True, exist_ok=True)

            (config_dir / "options.yml").write_text(
                "dataTypes: not-a-list\n"
                "databaseTypes:\n"
                "  - postgres\n"
                "dataPlatformTypes: 123\n"
            )
            (config_dir / "agent.yml").write_text(
                "eventStages: created\n"
            )
            (config_dir / "streamTemplate.txt").write_text("T")

            paths = SimpleNamespace(
                root_app_path=root,
                app_path=root / "app",
                config_path=config_dir,
                src_path=root / "app" / "src",
                api_path=root / "app" / "api",
                utils_path=root / "app" / "utils",
                static_path=root / "app" / "static",
            )

            ws = load_config(
                paths,
                debug_mode=False,
                app_path="app.main:app",
                app_port=8005,
                app_host="0.0.0.0",
            )

            self.assertEqual(ws.socket.dataTypes, [])
            self.assertEqual(ws.socket.databaseTypes, ["postgres"])
            self.assertEqual(ws.socket.dataPlatformTypes, [])
            self.assertEqual(ws.socket.eventStages, [])
            self.assertEqual(ws.socket.eventResponseTemplate, "T")


if __name__ == "__main__":
    unittest.main()