from __future__ import annotations

import unittest

from feishu_stack.models import OperationResult, to_dict


class ModelTests(unittest.TestCase):
    def test_operation_result_json_shape(self) -> None:
        result = OperationResult(
            ok=True,
            component="moonbridge",
            action="start",
            message="started",
            pid=123,
            port=38440,
            stdout_log="out.log",
            stderr_log="err.log",
            duration_ms=10,
        )
        data = to_dict(result)
        self.assertIs(data["ok"], True)
        self.assertEqual(data["component"], "moonbridge")
        self.assertEqual(data["action"], "start")
        self.assertEqual(data["pid"], 123)
        self.assertEqual(data["port"], 38440)
        self.assertEqual(data["stdout_log"], "out.log")
        self.assertEqual(data["stderr_log"], "err.log")
        self.assertEqual(data["duration_ms"], 10)

