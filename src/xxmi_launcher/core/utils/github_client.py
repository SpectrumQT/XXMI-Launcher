import requests

from typing import List
from dataclasses import dataclass

from dacite import from_dict


@dataclass
class ResponseReleaseAsset:
    name: str
    browser_download_url: str


@dataclass
class ResponseRelease:
    tag_name: str
    body: str
    assets: List[ResponseReleaseAsset]


class GitHubClient:
    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo

    def fetch_latest_release(self, asset_version_pattern, asset_name_format, signature_pattern=None):
        try:
            response = requests.get(f'https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest').json()
        except Exception as e:
            raise ValueError(f'Failed to establish HTTPS connection to GitHub!\n\n'
                             f'Please check your Antivirus, Firewall, Proxy and VPN settings.') from e

        if 'message' in response and 'API rate limit exceeded' in response['message']:
            raise ConnectionRefusedError('GitHub API rate limit exceeded!')

        try:
            response = from_dict(data_class=ResponseRelease, data=response)
        except Exception as e:
            raise ValueError(f'Failed to parse GitHub response!') from e

        result = asset_version_pattern.findall(response.tag_name)
        if len(result) != 1:
            raise ValueError('Failed to parse latest release version!')
        version = result[0]

        if signature_pattern is None:
            signature = None
        else:
            result = signature_pattern.findall(response.body)
            if len(result) != 1:
                raise ValueError('Failed to parse signature!')
            signature = result[0]

        for asset in response.assets:
            if asset.name == asset_name_format % version:
                release_notes = self.parse_release_notes(response.body)
                return version, asset.browser_download_url, signature, release_notes

        raise ValueError(f"Failed to locate asset matching to '{asset_name_format}'!")

    def download_data(self, url, block_size=4096, update_progress_callback=None):
        response = requests.get(url, stream=True)

        downloaded_bytes = 0
        total_bytes = int(response.headers.get("content-length", 0))
        if update_progress_callback is not None:
            update_progress_callback(downloaded_bytes, total_bytes)

        data = bytearray()
        for block_data in response.iter_content(block_size):
            data += block_data
            downloaded_bytes += len(block_data)
            if update_progress_callback is not None:
                update_progress_callback(downloaded_bytes, total_bytes)

        return data

    def parse_release_notes(self, body) -> str:
        # Skip warning section header to exclude it from search
        body = body.replace('## Warning', '')
        # Search for start of section
        start = body.find('##')
        if start == -1:
            return '<font color="red">⚠ Error! Invalid release notes format! ⚠</font>'
        # Search for start of signature section (footer)
        end = body.find('## Signature')
        if end == -1:
            return '<font color="red">☢ Error! Release is unsigned! ☢</font>'
        # Return text inbetween
        return body[start:end]