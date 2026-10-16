import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


# Isolate optional display libraries without changing imports in other tests.
spec = importlib.util.spec_from_file_location(
    "storage_clock",
    Path(__file__).resolve().parents[1] / "odroid_homecloud_display" / "clock.py",
)
assert spec is not None and spec.loader is not None
clock = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {
    name: MagicMock()
    for name in (
        "PIL",
        "luma",
        "luma.core",
        "luma.core.interface",
        "luma.core.interface.serial",
        "luma.core.render",
        "luma.oled",
        "luma.oled.device",
    )
}):
    spec.loader.exec_module(clock)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(patch.object(
            clock.shutil, "disk_usage",
            return_value=SimpleNamespace(used=2_000_000_000, total=8_000_000_000),
        ))
        self.which = self.enterContext(patch.object(
            clock.shutil, "which", return_value="/usr/sbin/zfs",
        ))
        self.command = self.enterContext(patch.object(
            clock, "command", return_value="1000000000\t3000000000\n",
        ))

    def test_unset_dataset_preserves_tank_default(self):
        self.assertEqual(clock.storage_lines(), [
            "sd: 2,0 / 8,0 GB",
            "tank: 1,0 / 4,0 GB",
        ])
        self.command.assert_called_once_with([
            "/usr/sbin/zfs", "list", "-Hp", "-o", "used,available", "tank",
        ])

    def test_pool_and_nested_dataset_change_query_and_label(self):
        for dataset in ("backup", "storage/media"):
            with self.subTest(dataset=dataset):
                os.environ["HOMECLOUD_ZFS_DATASET"] = dataset
                self.assertEqual(
                    clock.storage_lines()[1], f"{dataset}: 1,0 / 4,0 GB",
                )
                self.assertEqual(self.command.call_args.args[0][-1], dataset)

    def test_unavailable_zfs_keeps_configured_label(self):
        os.environ["HOMECLOUD_ZFS_DATASET"] = "backup"
        self.command.side_effect = subprocess.CalledProcessError(1, ["zfs"])
        self.assertEqual(clock.storage_lines()[1], "backup: unavailable")

    def test_missing_zfs_uses_fallback_path_and_unavailable_label(self):
        self.which.return_value = None
        self.command.side_effect = FileNotFoundError("zfs")
        self.assertEqual(clock.storage_lines()[1], "tank: unavailable")
        self.assertEqual(self.command.call_args.args[0][0], "/usr/sbin/zfs")

    def test_invalid_zfs_output_is_unavailable(self):
        self.command.return_value = "not numeric"
        self.assertEqual(clock.storage_lines()[1], "tank: unavailable")

    def test_empty_dataset_is_an_explicit_configuration_error(self):
        for value in ("", "   "):
            with self.subTest(value=value):
                os.environ["HOMECLOUD_ZFS_DATASET"] = value
                with self.assertRaisesRegex(
                    ValueError, "HOMECLOUD_ZFS_DATASET must not be empty",
                ):
                    clock.storage_lines()
        self.command.assert_not_called()

    def test_root_filesystem_failure_does_not_hide_zfs(self):
        with patch.object(clock.shutil, "disk_usage", side_effect=OSError):
            self.assertEqual(clock.storage_lines(), [
                "sd: unavailable",
                "tank: 1,0 / 4,0 GB",
            ])


if __name__ == "__main__":
    unittest.main()
