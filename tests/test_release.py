from hashlib import sha256
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location(
    "release", Path(__file__).resolve().parent.parent / "scripts/release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_unverified_executable_is_rejected(self):
        import io
        expected = {'packaged_executable_sha256': sha256(b'verified icon runtime').hexdigest(),
                    'app_asar_sha256': sha256(b'verified app').hexdigest()}
        for binary, app, valid in [(b'verified icon runtime', b'verified app', True),
                                   (b'arbitrary runtime edit', b'verified app', False),
                                   (b'verified icon runtime', b'tampered app', False)]:
            data = io.BytesIO()
            with zipfile.ZipFile(data, 'w') as output:
                output.writestr('app/Chickadee.exe', binary)
                output.writestr('app/resources/app.asar', app)
            with zipfile.ZipFile(data) as archive:
                if valid:
                    release.verify_vendor_runtime(archive, 'app/', expected)
                else:
                    with self.assertRaisesRegex(ValueError, 'verified Electron runtime'):
                        release.verify_vendor_runtime(archive, 'app/', expected)

    def test_windows_extraction_rejects_the_reported_chromium_path(self):
        name = ('Chickadee-0.10.6/resources/engine/_internal/playwright/driver/package/'
                '.local-browsers/chromium_headless_shell-1248/chrome-headless-shell-win64/'
                'resources/accessibility/reading_mode_gdocs_helper_manifest.json')
        with self.assertRaisesRegex(ValueError, 'Windows extraction path too long'):
            release.validate_zip_paths([name])
        release.validate_zip_paths([name.replace('playwright/driver/package/.local-browsers/', 'browsers/')])

    def test_windows_path_budget_counts_utf16_units(self):
        release.validate_zip_paths(['a' * 179])
        with self.assertRaisesRegex(ValueError, 'Windows extraction path too long'):
            release.validate_zip_paths(['a' * 178 + '\U0001f426'])

    def test_path_check_is_enforced_for_an_otherwise_valid_zip(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            archive = self.make_archive(directory)
            with zipfile.ZipFile(archive, 'a') as output:
                output.writestr('Chickadee-0.6.2/' + 'x' * 180, 'fixture')
            archive.with_suffix('.zip.sha256').write_text(
                f'{sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n', encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'Windows extraction path too long'):
                release.verify('0.6.2', directory)

    def make_archive(self, directory, include_browser=True, browser_name="chrome-headless-shell.exe"):
        value = "0.6.2"
        archive = directory / f"Chickadee-Studio-{value}-win-x64.zip"
        files = [
            "Chickadee.exe", "resources/app.asar",
            "resources/engine/ChickadeeEngine.exe", "README_FIRST.txt",
            "docs/quickstart-windows.md", "licenses/Frontend-Third-Party.txt",
        ]
        if include_browser:
            files.append(f"resources/engine/_internal/playwright/driver/package/.local-browsers/chromium_headless_shell-1/chrome-win/{browser_name}")
        with zipfile.ZipFile(archive, "w") as output:
            for name in files:
                output.writestr(f"Chickadee-{value}/{name}", "fixture")
        digest = sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix(".zip.sha256").write_text(
            f"{digest}  {archive.name}\n", encoding="ascii"
        )
        return archive

    def test_complete_distribution_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.make_archive(directory)
            release.verify("0.6.2", directory)

    def test_tampered_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            archive = self.make_archive(directory)
            with archive.open("ab") as stream:
                stream.write(b"tampered")
            with self.assertRaisesRegex(ValueError, "SHA256"):
                release.verify("0.6.2", directory)

    def test_legacy_browser_name_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.make_archive(directory, browser_name="headless_shell.exe")
            release.verify("0.6.2", directory)

    def test_missing_browser_is_rejected_even_with_valid_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.make_archive(directory, include_browser=False)
            with self.assertRaisesRegex(ValueError, "Chromium"):
                release.verify("0.6.2", directory)
