from __future__ import annotations

import socket
import tempfile
import unittest
from pathlib import Path

from feishu_stack.logs import tail
from feishu_stack.process import is_port_listening, read_pid, write_pid


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

