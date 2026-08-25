from __future__ import annotations

import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'backup_manifest.py'


class BackupBundleTests(unittest.TestCase):
    def run_manifest(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_ops_007_local_bundle_verifies_then_refuses_tamper(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw)
            (bundle / 'database.dump.enc').write_bytes(b'encrypted-db-evidence')
            (bundle / 'media.tar.enc').write_bytes(b'encrypted-media-evidence')
            (bundle / 'sentinel.txt').write_text('sentinel-token', encoding='utf-8')
            created = self.run_manifest(
                'create', '--bundle', str(bundle), '--media-mode', 'local',
                '--artifact', 'database=database.dump.enc',
                '--artifact', 'media=media.tar.enc',
                '--artifact', 'sentinel=sentinel.txt',
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            verified = self.run_manifest('verify', '--bundle', str(bundle))
            self.assertEqual(verified.returncode, 0, verified.stderr)

            (bundle / 'media.tar.enc').write_bytes(b'tampered')
            rejected = self.run_manifest('verify', '--bundle', str(bundle))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('checksum', rejected.stderr.lower())

    def test_ops_007_bundle_requires_database_and_media_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw)
            (bundle / 'database.dump.enc').write_bytes(b'db')
            missing = self.run_manifest(
                'create', '--bundle', str(bundle), '--media-mode', 'local',
                '--artifact', 'database=database.dump.enc',
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('media', missing.stderr.lower())

    def test_ops_007_s3_bundle_requires_inventory_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw)
            (bundle / 'database.dump.enc').write_bytes(b'db')
            (bundle / 's3-inventory.json.enc').write_bytes(b'inventory')
            (bundle / 'sentinel.txt').write_text('sentinel-token', encoding='utf-8')
            created = self.run_manifest(
                'create', '--bundle', str(bundle), '--media-mode', 's3',
                '--artifact', 'database=database.dump.enc',
                '--artifact', 's3_inventory=s3-inventory.json.enc',
                '--artifact', 'sentinel=sentinel.txt',
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(self.run_manifest('verify', '--bundle', str(bundle)).returncode, 0)

    def test_ops_007_media_restore_rejects_link_members(self):
        validator = ROOT / 'scripts' / 'validate-backup-tar.py'
        with tempfile.TemporaryDirectory() as raw:
            archive = Path(raw) / 'media.tar'
            with tarfile.open(archive, 'w') as handle:
                link = tarfile.TarInfo('./escape-link')
                link.type = tarfile.SYMTYPE
                link.linkname = '../../outside'
                handle.addfile(link)
            result = subprocess.run([sys.executable, str(validator), str(archive)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unsafe', result.stderr.lower())


if __name__ == '__main__':
    unittest.main()
