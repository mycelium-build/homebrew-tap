import unittest
from unittest.mock import patch
import update


def release(tag, **kwargs):
    return dict(tag_name=tag, draft=kwargs.get('draft', False),
                prerelease=kwargs.get('prerelease', '-rc.' in tag))


class ReleaseTests(unittest.TestCase):
    def test_channels_drafts_flags_and_numeric_order(self):
        releases = [release('v1.2.0-rc.9'), release('v1.2.0-rc.10'),
                    release('v2.0.0-rc.1', draft=True), release('v1.2.0'),
                    release('v3.0.0', prerelease=True), release('v99.0.0-beta.1')]
        self.assertEqual(update.latest(releases, 'preview')['tag_name'], 'v1.2.0-rc.10')
        self.assertEqual(update.latest(releases, 'stable')['tag_name'], 'v1.2.0')

    def test_missing_channel_does_not_fall_back_to_stable(self):
        with self.assertRaises(ValueError):
            update.latest([release('v1.2.0')], 'preview')

    def test_input_cannot_be_a_ref_or_shell_expression(self):
        for tag in ('main', '../v1.0.0', 'v01.0.0', 'v1.0.0-rc.01', 'v1.0.0;echo bad'):
            with self.assertRaises(ValueError):
                update.channel_of(tag)

    def test_asset_identity_digest_and_duplicates(self):
        r = release('v1.2.0')
        r['assets'] = [dict(name=f'Datalith_1.2.0_{arch}.dmg',
                            browser_download_url=f'https://github.com/{update.REPOSITORY}/releases/download/v1.2.0/Datalith_1.2.0_{arch}.dmg',
                            digest='sha256:' + 'a' * 64) for arch in ('aarch64', 'x64')]
        self.assertEqual(len(update.assets_for(r)), 2)
        with patch.dict(r['assets'][0], browser_download_url='https://example.org/evil.dmg'):
            with self.assertRaises(ValueError):
                update.assets_for(r)
        with patch.dict(r['assets'][0], digest=None):
            with self.assertRaises(ValueError):
                update.assets_for(r)
        r['assets'].append(r['assets'][0])
        with self.assertRaises(ValueError):
            update.assets_for(r)
        r['assets'] = r['assets'][:1]
        with self.assertRaises(ValueError):
            update.assets_for(r)


if __name__ == '__main__':
    unittest.main()
