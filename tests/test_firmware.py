"""Tests of the older command-line tools in tools/ (they call the epm2mod package).

Run: python3 -m unittest discover -s tests

Tests that need firmware BINs are skipped when the files are absent.
"""

import contextlib, glob, hashlib, io, json, os, pathlib, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import oetool  # noqa: E402
import build  # noqa: E402

STOCK = sorted(glob.glob(os.path.join(ROOT, "firmware/stock/E-PM2/*.BIN")))


class TestScramble(unittest.TestCase):
    def test_encode_decode_inverse(self):
        data = bytes(range(256)) * 4
        self.assertEqual(oetool.decode(oetool.encode(data)), data)
        self.assertNotEqual(oetool.encode(data), data)


@unittest.skipUnless(STOCK, "stock firmware not present")
class TestStock(unittest.TestCase):
    def test_round_trip_all_versions(self):
        for path in STOCK:
            with self.subTest(path=os.path.basename(path)):
                raw = pathlib.Path(path).read_bytes()
                blocks, tail = oetool.parse(raw)
                self.assertTrue(all(b["ok"] for b in blocks))
                self.assertEqual(oetool.build(blocks, tail), raw)


@unittest.skipUnless(STOCK, "stock firmware not present")
class TestPatchSpecs(unittest.TestCase):
    def test_specs_with_expected_hash_reproduce(self):
        for spec in glob.glob(os.path.join(ROOT, "patches/*.json")):
            s = json.loads(pathlib.Path(spec).read_text(encoding="utf-8"))
            if not s.get("expected_sha256"):
                continue
            with self.subTest(spec=os.path.basename(spec)), tempfile.TemporaryDirectory() as folder:
                out = os.path.join(folder, s["name"] + ".BIN")
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertTrue(build.build([spec], out))
                self.assertEqual(hashlib.sha256(pathlib.Path(out).read_bytes()).hexdigest(), s["expected_sha256"])


if __name__ == "__main__":
    unittest.main()
