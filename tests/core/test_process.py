from __future__ import annotations

import socket
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from feishu_stack.logs import tail
from feishu_stack.process import is_port_listening, read_pid, start_process, stop_component, write_pid
from feishu_stack.core import process as process_module


class ProcessTests(unittest.TestCase):
    def test_pid_file_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.pid"
            self.assertIsNone(read_pid(path))
            write_pid(path, 456)
            self.assertEqual(read_pid(path), 456)


    def test_port_detection(self) -> None:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        try:
            port = sock.getsockname()[1]
            self.assertTrue(is_port_listening(port))
        finally:
            sock.close()


    def test_log_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.log"
            path.write_text("a\nb\nc\n", encoding="utf-8")
            result = tail(path, lines=2)
            self.assertEqual(result.lines, ["b", "c"])

    def test_stop_refuses_unverified_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "component.pid"
            write_pid(pid_file, 1234)
            with mock.patch.object(process_module, "process_info", return_value=(True, "python.exe")), \
                 mock.patch.object(process_module, "process_matches", return_value=False), \
                 mock.patch.object(process_module, "terminate_pid") as terminate, \
                 mock.patch.object(process_module, "is_port_listening", return_value=False):
                result = stop_component("sample", pid_file, None)
            terminate.assert_not_called()
            self.assertIn("Refused to terminate", result.message)
            self.assertFalse(pid_file.exists())

    def test_start_process_uses_windowless_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_proc = mock.Mock(pid=1234)
            with mock.patch.object(process_module, "open_rotating", side_effect=[mock.Mock(), mock.Mock()]), \
                 mock.patch.object(process_module.subprocess, "Popen", return_value=fake_proc) as popen:
                result = start_process(["node", "server.js"], root, root / "out.log", root / "err.log")

            self.assertEqual(result.pid, 1234)
            _, kwargs = popen.call_args
            self.assertEqual(kwargs["creationflags"], process_module.WINDOWLESS_PROCESS_FLAGS)
            if process_module.os.name == "nt":
                self.assertIsNotNone(kwargs["startupinfo"])
