from __future__ import annotations

import hashlib
import unittest

from backend.platform_core.domain.media_assets import (
    build_media_metadata,
    public_download_allowed,
)


class MediaAssetDomainTests(unittest.TestCase):
    def test_media_001_upload_metadata_is_safe_complete_and_immutable(self):
        payload = b"image payload"

        metadata = build_media_metadata(
            original_name="../../unsafe portrait (final).PNG",
            content_type="IMAGE/PNG",
            payload=payload,
            visibility="private",
            decorative=False,
        )

        self.assertEqual(metadata["original_name"], "unsafe portrait (final).PNG")
        self.assertEqual(metadata["storage_name"], "unsafe_portrait_final.PNG")
        self.assertEqual(metadata["mime_type"], "image/png")
        self.assertEqual(metadata["file_size"], len(payload))
        self.assertEqual(metadata["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(metadata["visibility"], "private")
        self.assertFalse(metadata["decorative"])

    def test_media_002_public_download_requires_public_and_clean_scan(self):
        self.assertTrue(public_download_allowed("public", "clean"))
        self.assertFalse(public_download_allowed("private", "clean"))
        self.assertFalse(public_download_allowed("public", "unavailable"))
        self.assertFalse(public_download_allowed("public", "pending"))
        self.assertFalse(public_download_allowed("public", "infected"))

    def test_media_003_invalid_visibility_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "visibility"):
            build_media_metadata(
                original_name="asset.png",
                content_type="image/png",
                payload=b"x",
                visibility="world",
                decorative=True,
            )


if __name__ == "__main__":
    unittest.main()
