import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
XDB_PATH = DATA_DIR / "ip2region_v4.xdb"
MAKER_IMAGE = os.environ.get(
    "IP2REGION_MAKER_IMAGE",
    "local/ip2region-maker:latest",
)
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
REGION_RE = re.compile(r"\{region:(.*?), iocount:")


class IPv4XDBOutputTest(unittest.TestCase):
    CASES = (
        ("1.0.1.1", "中国", None),
        ("1.178.1.1", "美国", "俄勒冈州"),
        ("1.36.0.1", "香港(中国)", None),
        ("27.109.128.1", "澳门(中国)", None),
        ("78.160.0.1", "土尔其", None),
    )

    @classmethod
    def setUpClass(cls):
        if not XDB_PATH.is_file():
            raise unittest.SkipTest(f"IPv4 XDB 文件不存在: {XDB_PATH}")
        if shutil.which("docker") is None:
            raise unittest.SkipTest("未安装 Docker，无法运行 XDB 集成测试")

        inspect = subprocess.run(
            ["docker", "image", "inspect", MAKER_IMAGE],
            capture_output=True,
            text=True,
        )
        if inspect.returncode != 0:
            raise unittest.SkipTest(
                f"Docker 镜像不可用: {MAKER_IMAGE}; {inspect.stderr.strip()}"
            )

    def test_selected_ip_country_and_state_output(self):
        command_input = "\n".join(ip for ip, _, _ in self.CASES) + "\nquit\n"
        result = subprocess.run(
            [
                "docker",
                "run",
                "-i",
                "--rm",
                "-v",
                f"{DATA_DIR}:/app/data:ro",
                MAKER_IMAGE,
                "search",
                "--db=/app/data/ip2region_v4.xdb",
            ],
            input=command_input,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(
            0,
            result.returncode,
            msg=f"xdb search 执行失败:\n{result.stdout}\n{result.stderr}",
        )

        output = ANSI_ESCAPE_RE.sub("", result.stdout + result.stderr)
        regions = REGION_RE.findall(output)
        self.assertEqual(
            len(self.CASES),
            len(regions),
            msg=f"查询结果数量不符:\n{output}",
        )

        for (ip, expected_country, expected_province), region in zip(
            self.CASES, regions
        ):
            fields = region.split("|")
            with self.subTest(ip=ip, region=region):
                self.assertGreaterEqual(len(fields), 3)
                self.assertEqual(expected_country, fields[1])
                if expected_province is not None:
                    self.assertEqual(expected_province, fields[2])
