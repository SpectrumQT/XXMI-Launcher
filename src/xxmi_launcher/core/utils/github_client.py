import requests

from typing import List, Optional
from dataclasses import dataclass

from dacite import from_dict
from requests.exceptions import SSLError

from core.utils.proxy import ProxyConfig, ProxyManager


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
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.access_token = ''
        self.verify_ssl = False

    def configure(self, access_token: Optional[str], verify_ssl: Optional[bool], proxy_config: Optional[ProxyConfig]):
        if access_token is not None:
            self.access_token = access_token.strip()
        if verify_ssl is not None:
            self.verify_ssl = verify_ssl
        if proxy_config is not None:
            self.proxy_manager.configure(proxy_config)

    def fetch_latest_release(self, repo_owner, repo_name,
                             asset_version_pattern, asset_name_format, signature_pattern=None):
        headers = {}

        if self.access_token:
            headers['Authorization'] = f'token {self.access_token}'

        try:
            response = requests.get(
                url=f'https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest',
                headers=headers,
                proxies=self.proxy_manager.proxies,
                timeout=10,
                verify=self.verify_ssl
            ).json()
        except SSLError as e:
            raise ValueError(f'Failed to validate SSL certificate of GitHub HTTPS connection!\n\n'
                             f'If you trust your proxy, uncheck *Verify SSL* in *Launcher Settings* and try again.') from e
        except Exception as e:
            raise ValueError(f'Failed to establish HTTPS connection to GitHub!\n\n'
                             f'Please check your Antivirus, Firewall, Proxy and VPN settings.') from e

        message, status = response.get('message', None), response.get('status', 0)

        if message is not None:
            message = message.lower()
            status = int(status)
            if 'rate limit' in message:
                raise ConnectionRefusedError('GitHub API rate limit exceeded!')
            elif 'bad credentials' in message or status == 401:
                raise ConnectionError('GitHub Personal Access Token is invalid!\n\n'
                                      'Please configure correct token in launcher settings.')

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

        release_notes = self.parse_release_notes(response.body)

        asset_download_url, manifest_download_url = None, None

        for asset in response.assets:
            if asset.name == asset_name_format % version:
                asset_download_url = asset.browser_download_url
            elif asset.name == 'Manifest.json':
                manifest_download_url = asset.browser_download_url

        if asset_download_url is None:
            raise ValueError(f"Failed to locate asset matching to '{asset_name_format}'!")

        return version, asset_download_url, signature, release_notes, manifest_download_url

    def download_data(self, url, block_size=4096, update_progress_callback=None):
        headers = {}

        if self.access_token:
            headers['Authorization'] = f'token {self.access_token}'

        response = requests.get(
            url=url,
            headers=headers,
            proxies=self.proxy_manager.proxies,
            verify=self.verify_ssl,
            timeout=10,
            stream=True
        )

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
