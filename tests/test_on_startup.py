# tests/test_on_startup.py

import os
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from app.utils.on_startup import get_workspace, run_checks_on_startup  # noqa: E402
from app.utils.loader import Config, AgentConfig, SocketConfig, load_config  # noqa: E402

class TestOnStartup(unittest.TestCase):
    def setUp(self):
        self._env_snapshot = dict(os.environ)
        get_workspace.cache_clear()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_snapshot)
        get_workspace.cache_clear()

    def _dummy_paths(self, root: Path, config_dir: Path):
        # WorkspacePaths is a dataclass in app.utils.paths; however load_config only
        # requires an object with .config_path (and later Config expects the full object).
        # For tests we can use a SimpleNamespace with the same attributes.
        return SimpleNamespace(
            root_app_path=root,
            app_path=root / "app",
            config_path=config_dir,
            src_path=root / "app" / "src",
            api_path=root / "app" / "api",
            utils_path=root / "app" / "utils",
            static_path=root / "app" / "static",
        )

    def _dummy_config(self, paths, debug_mode: bool) -> Config:
        # Align with current dataclasses in app/utils/loader.py
        return Config(
            dir=paths,
            agent=AgentConfig(
                dataIngestion={},
                dataCleaning={},
                dataAnalytics={},
                dataQuality={},
            ),
            socket=SocketConfig(
                dataTypes=[],
                databaseTypes=[],
                dataPlatformTypes=[],
                eventStages=[],
                eventResponseTemplate="T",
            ),
            debug_mode=debug_mode,
            app_path="app.main:app",
            app_port=8005,
            app_host="0.0.0.0",
            secrets=SimpleNamespace(
                jupyter_kernel_server_url="http://localhost:8888",
                jupyter_kernel_server_timeout=30,
                jupyter_kernel_server_socket="/tmp/jupyter.sock",
                _hf_token="fake-hf-token",
                _jupyter_kernel_server_key="fake-jupyter-key",
            ) # type: ignore
        )

    def test_run_checks_on_startup_prod_rejects_dev_config_path(self):
        # run_checks_on_startup only enforces "prod must not point at dev config"
        paths = self._dummy_paths(root=Path("/x/y"), config_dir=Path("/x/y/app/config/dev"))
        ws = self._dummy_config(paths, debug_mode=False)

        with self.assertRaises(EnvironmentError):
            run_checks_on_startup(ws)

    def test_load_config_prod_missing_required_files(self):
        # Missing-required-files check lives in load_config(), not run_checks_on_startup()
        with TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "app" / "config" / "prod"
            config_dir.mkdir(parents=True, exist_ok=True)

            paths = self._dummy_paths(root=root, config_dir=config_dir)

            with self.assertRaises(FileNotFoundError):
                load_config(
                    paths,
                    debug_mode=False,
                    app_path="app.main:app",
                    app_port=8005,
                    app_host="0.0.0.0",
                )

    def test_get_workspace_is_cached_singleton_per_process(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "app" / "config" / "prod"
            config_dir.mkdir(parents=True, exist_ok=True)

            # Ensure required files exist so load_config can succeed if it were called.
            # In this test we patch load_config anyway, but keeping them valid helps future-proofing.
            (config_dir / "options.yml").write_text(
                "dataTypes: []\n"
                "databaseTypes: []\n"
                "dataPlatformTypes: []\n"
                "eventStages: []\n"
            )
            # agent.yml is a mapping; set keys to null so load_agent_config won't try to load sub-files
            (config_dir / "agent.yml").write_text(
                "dataIngestion: null\n"
                "dataCleaning: null\n"
                "dataAnalytics: null\n"
                "dataQuality: null\n"
            )
            (config_dir / "streamTemplate.txt").write_text("T")

            fake_paths = self._dummy_paths(root=root, config_dir=config_dir)

            os.environ["DEV_MODE"] = "false"

            dummy_ws = self._dummy_config(fake_paths, debug_mode=False)

            with patch("app.utils.on_startup.resolve_paths", return_value=fake_paths) as rp, \
                 patch("app.utils.on_startup.load_config", return_value=dummy_ws) as lc:

                ws1 = get_workspace()
                ws2 = get_workspace()

            self.assertIs(ws1, ws2)
            rp.assert_called_once()
            lc.assert_called_once()

    def test_get_workspace_reads_env_overrides(self):
        """
        Ensure env vars are read and passed to load_config.
        """
        with TemporaryDirectory() as td:
            root = Path(td)
            config_dir = root / "app" / "config" / "prod"
            config_dir.mkdir(parents=True, exist_ok=True)

            fake_paths = self._dummy_paths(root=root, config_dir=config_dir)

            os.environ["DEV_MODE"] = "true"
            os.environ["FASTAPI_APP_PATH"] = "app.main:app"
            os.environ["APP_PORT"] = "9999"
            os.environ["APP_HOST"] = "127.0.0.1"

            dummy_ws = self._dummy_config(fake_paths, debug_mode=True)

            with patch("app.utils.on_startup.resolve_paths", return_value=fake_paths), \
                 patch("app.utils.on_startup.run_checks_on_startup"), \
                 patch("app.utils.on_startup.load_config", return_value=dummy_ws) as lc:

                _ = get_workspace()

            _, kwargs = lc.call_args
            self.assertTrue(kwargs["debug_mode"])
            self.assertEqual(kwargs["app_path"], "app.main:app")
            self.assertEqual(kwargs["app_port"], 9999)
            self.assertEqual(kwargs["app_host"], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()