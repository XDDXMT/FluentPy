"""Publishing defaults to checks only and uploads the exact reviewed artifacts."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_pypi', ROOT / 'scripts/publish_pypi.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PyPIReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.directory = self.root / 'dist/pypi/0.6.9'
        self.directory.mkdir(parents=True)
        (self.root / 'pyproject.toml').write_text('[project]\nversion = "0.6.9"\n', encoding='utf-8')
        self.manifest = {'name': publisher.NAME, 'version': '0.6.9', 'files': {}}
        for suffix in ('py3-none-any', 'cp313-cp313-win_amd64'):
            path = self.directory / f'fluentpy_qt-0.6.9-{suffix}.whl'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('fluentpy_qt-0.6.9.dist-info/METADATA',
                    'Metadata-Version: 2.4\nName: fluentpy-qt\nVersion: 0.6.9\n\n')
            self.manifest['files'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.save_manifest()

    def tearDown(self):
        self.temporary.cleanup()

    def save_manifest(self):
        (self.directory / 'release.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def test_default_only_checks_and_never_contacts_or_uploads_to_pypi(self):
        with patch.object(publisher, 'ROOT', self.root), patch.object(publisher.subprocess, 'run') as run, \
                patch.object(publisher, 'remote_files') as remote, contextlib.redirect_stdout(io.StringIO()):
            publisher.main([])
        self.assertEqual(run.call_count, 1)
        self.assertIn('check', run.call_args.args[0])
        self.assertNotIn('upload', run.call_args.args[0])
        remote.assert_not_called()

    def test_changed_artifact_is_rejected_before_any_command(self):
        path = self.directory / next(iter(self.manifest['files']))
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed after preparation'):
            publisher.checked_artifacts(self.directory)

    def test_manifest_cannot_publish_a_version_other_than_the_project(self):
        (self.root / 'pyproject.toml').write_text('[project]\nversion = "0.7.0"\n', encoding='utf-8')
        future = self.root / 'dist/pypi/0.7.0'
        future.parent.mkdir(parents=True, exist_ok=True)
        self.directory.rename(future)
        with patch.object(publisher, 'ROOT', self.root), patch.object(publisher.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'does not match the project version'):
                publisher.main(['--upload'])
        run.assert_not_called()

    def test_traversal_and_unexpected_metadata_are_rejected(self):
        first, digest = next(iter(self.manifest['files'].items()))
        for filename in ('../outside.whl', '..\\outside.whl'):
            self.manifest['files'] = {filename: digest}
            self.save_manifest()
            with self.assertRaisesRegex(ValueError, 'local ordinary files'):
                publisher.checked_artifacts(self.directory)
        self.manifest['files'] = {first: digest}
        self.manifest['version'] = '0.7.0'
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'Unexpected project or version'):
            publisher.checked_artifacts(self.directory)

    def test_upload_resumes_matching_files_and_ignores_unlisted_packages(self):
        paths = [self.directory / name for name in self.manifest['files']]
        (self.directory / 'unreviewed.whl').write_bytes(b'not part of release')
        existing = {paths[0].name: self.manifest['files'][paths[0].name]}
        with patch.object(publisher, 'ROOT', self.root), patch.object(publisher.subprocess, 'run') as run, \
                patch.object(publisher, 'remote_files', side_effect=[existing, self.manifest['files']]), \
                patch.dict(publisher.os.environ, {'TWINE_PASSWORD': 'do-not-use', 'TWINE_REPOSITORY_URL': 'https://invalid.example'}), \
                contextlib.redirect_stdout(io.StringIO()):
            publisher.main(['--upload'])
        upload = run.call_args_list[1]
        command = upload.args[0]
        self.assertIn(publisher.UPLOAD_URL, command)
        self.assertIn(str(paths[1]), command)
        self.assertNotIn(str(paths[0]), command)
        self.assertNotIn(str(self.directory / 'unreviewed.whl'), command)
        self.assertNotIn('TWINE_PASSWORD', upload.kwargs['env'])
        self.assertEqual(upload.kwargs['env']['PYTHON_KEYRING_BACKEND'], 'keyring.backends.null.Keyring')
        self.assertIn('--config-file', command)

    def test_different_remote_file_cannot_be_replaced(self):
        paths = [self.directory / name for name in self.manifest['files']]
        with self.assertRaisesRegex(ValueError, 'different file'):
            publisher.pending_artifacts(self.manifest, paths, {paths[0].name: 'not-the-reviewed-hash'})

    def test_incomplete_remote_verification_is_not_reported_as_success(self):
        with patch.object(publisher, 'ROOT', self.root), patch.object(publisher.subprocess, 'run'), \
                patch.object(publisher, 'remote_files', return_value={}), patch.object(publisher.time, 'sleep'), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'public index is still synchronizing'):
                publisher.main(['--upload'])

    def test_public_index_can_appear_in_multiple_steps_after_upload(self):
        paths = [self.directory / name for name in self.manifest['files']]
        first = {paths[0].name: self.manifest['files'][paths[0].name]}
        with patch.object(publisher, 'remote_files', side_effect=[{}, first, self.manifest['files']]), \
                patch.object(publisher.time, 'sleep') as sleep, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(publisher.wait_for_publication(self.manifest, paths, delays=(0, 1, 2)))
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])

    def test_verification_retry_budget_is_bounded(self):
        paths = [self.directory / name for name in self.manifest['files']]
        with patch.object(publisher, 'remote_files', return_value={}) as remote, \
                patch.object(publisher.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(publisher.wait_for_publication(self.manifest, paths, delays=(0, 1)))
        self.assertEqual(remote.call_count, 2)

    def test_verification_only_never_uploads_or_reads_credentials(self):
        with patch.object(publisher, 'ROOT', self.root), patch.object(publisher.subprocess, 'run') as run, \
                patch.object(publisher, 'remote_files', return_value=self.manifest['files']), \
                contextlib.redirect_stdout(io.StringIO()):
            publisher.main(['--verify-published'])
        self.assertEqual(run.call_count, 1)
        self.assertNotIn('upload', run.call_args.args[0])

    def test_verification_rejects_hash_mismatch_immediately(self):
        paths = [self.directory / name for name in self.manifest['files']]
        with patch.object(publisher, 'remote_files', return_value={paths[0].name: 'wrong'}), \
                patch.object(publisher.time, 'sleep') as sleep:
            with self.assertRaisesRegex(ValueError, 'different file'):
                publisher.wait_for_publication(self.manifest, paths)
        sleep.assert_not_called()
