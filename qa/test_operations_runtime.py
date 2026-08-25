from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OperationsRuntimeContracts(unittest.TestCase):
    def text(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding='utf-8')

    def test_ops_001_workers_wait_for_successful_migration_and_backend_readiness(self):
        compose = self.text('docker-compose.prod.yml')
        worker = compose.split('  worker:', 1)[1].split('  beat:', 1)[0]
        beat = compose.split('  beat:', 1)[1].split('  frontend:', 1)[0]
        backend = compose.split('  backend:', 1)[1].split('  worker:', 1)[0]
        for service in (worker, beat):
            self.assertIn('migrate: {condition: service_completed_successfully}', service)
        self.assertIn('/api/ready/', backend)

    def test_ops_007_backup_covers_database_storage_and_verified_sentinel(self):
        backup = self.text('scripts/backup.sh')
        restore = self.text('scripts/restore.sh')
        for token in ('database.dump.enc', 'media.tar.enc', 's3-inventory.json.enc', 'backup_manifest.py', 'backup_sentinel create'):
            self.assertIn(token, backup)
        for token in ('backup_manifest.py verify', 'validate-backup-tar.py', 'backup_sentinel verify', '/api/ready/'):
            self.assertIn(token, restore)

    def test_ops_008_systemd_schedule_and_operational_checks_are_present(self):
        self.assertTrue((ROOT / 'deploy/lodgeflow-backup.service').is_file())
        self.assertTrue((ROOT / 'deploy/lodgeflow-backup.timer').is_file())
        monitor = self.text('scripts/ops-monitor.py')
        for token in ('BACKUP_STATUS_FILE', 'BACKUP_MAX_AGE_HOURS', 'DISK_WARN_PERCENT', 'backup_stale', 'disk_capacity'):
            self.assertIn(token, monitor)

    def test_shell_scripts_parse(self):
        result = subprocess.run(['bash', '-n', *[str(path) for path in sorted((ROOT / 'scripts').glob('*.sh'))]], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ops_002_frontend_dependencies_are_locked_and_ci_uses_clean_install(self):
        self.assertTrue((ROOT / 'frontend/package-lock.json').is_file())
        self.assertIn('RUN npm ci --include=dev', self.text('frontend/Dockerfile'))
        self.assertIn('run: npm ci', self.text('.github/workflows/ci.yml'))

    def test_qa_003_role_matrix_has_deterministic_fixture_and_browser_contract(self):
        seed = self.text('backend/platform_core/management/commands/seed_local_demo.py')
        e2e = self.text('frontend/e2e/role-matrix.spec.ts')
        for role in ('secretary', 'treasurer', 'membership', 'mentor', 'auditor', 'viewer'):
            self.assertIn(f'"{role}"', seed)
            self.assertIn(f"'{role}'", e2e)
        self.assertIn('LOCAL_ROLE_PASSWORD', seed)
        self.assertIn('expectedAllowed', e2e)
        self.assertIn('expectedForbidden', e2e)


if __name__ == '__main__':
    unittest.main()
