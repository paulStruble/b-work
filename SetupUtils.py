import shutil
import zipfile
from pathlib import Path
import requests
import platform
import sys


class SetupUtils:
    _chrome_for_testing_url = "https://googlechromelabs.github.io/chrome-for-testing/"
    _last_known_good_versions_with_downloads = "last-known-good-versions-with-downloads.json"
    _known_good_versions_with_downloads = "known-good-versions-with-downloads.json"
    _browser_path = Path.cwd() / 'Browser'

    @staticmethod
    def get_platform() -> str:
        """Automatically detect the user's current platform (operating system).

        Prompt the user to manually select platform if the detected platform is incompatible.

        Returns:
            User's current platform if compatible.
        """
        system = platform.system()
        machine = platform.machine()
        is_64bits = sys.maxsize > 2 ** 32

        if system == "Windows":
            if is_64bits:
                return "win64"
            else:
                return "win32"
        elif system == "Darwin":
            if machine == "x86_64":
                return "mac-x64"
            elif machine == "arm64":
                return "mac-arm64"
        elif system == "Linux":
            if is_64bits:
                return "linux64"

        #  Unsupported/undetected: manual input
        else:
            options = [1, 2, 3, 4, 5]
            choice = None

            print('-' * (shutil.get_terminal_size().columns - 1))  # Horizontal line (cosmetic)
            print("Platform detection failed or platform not supported.\n"
                  "Please manually select a supported platform from the list below:\n\n"
                  "1. linux64\n"
                  "2. mac-arm64\n"
                  "3. mac-x64\n"
                  "4. win32\n"
                  "5. win64\n")
            print('-' * (shutil.get_terminal_size().columns - 1))  # Horizontal line (cosmetic)

            while choice not in options:
                choice = input("Input: ")

            match choice:
                case 1: return "linux64"
                case 2: return "mac-arm64"
                case 3: return "mac-x64"
                case 4: return "win32"
                case 5: return "win64"

    @staticmethod
    def get_latest_download_link(item: str, channel='Stable', user_platform='win64') -> tuple[str, str]:
        """Fetch the version number and download link for the latest version of the given item.

        Args:
            item: The download link to fetch (e.g. 'chrome', 'chromedriver', etc.)
            channel: Channel to download (e.g. 'Stable', 'Beta', etc.).
            user_platform: Current user platform (operating system).

        Returns:
            Tuple of ([latest version], [link to download])
        """
        print(f"Fetching download link for latest [{channel}] [{user_platform}] version of [{item}] ...")
        response = requests.get(SetupUtils._chrome_for_testing_url +
                                SetupUtils._last_known_good_versions_with_downloads)
        response.raise_for_status()
        latest_json = response.json()  # JSON object of all latest versions
        version = latest_json['channels'][channel]['version']
        downloads = latest_json['channels'][channel]['downloads'][item]

        # Return link for specified platform
        for d in downloads:
            if d['platform'] == user_platform:
                url = d['url']
                print(f"Download link for [{item}] version [{version}]: {url}")
                return version, url

    # TODO: update config with paths to chrome, chromedriver? - maybe just add options and set to default
    @staticmethod
    def download_browser_items(version=None, download_dir=_browser_path, channel='Stable', user_platform='win64') -> str:
        """Download and unzip latest Chrome and chromedriver versions to the specified directory.

        Args:
            download_dir: Directory to download files to.
            channel: Channel to download (e.g. 'Stable', 'Beta', etc.).
            user_platform: Current user platform (operating system).

        Returns:
            Version number of download (e.g. 125-0-6422-78)
        """
        # Download items
        for item in ('chrome', 'chromedriver'):
            if version is None:  # Get latest version if none specified.
                version, url = SetupUtils.get_latest_download_link(item, channel=channel, user_platform=user_platform)
            else:  # Fetch download link if version is specified.
                url = SetupUtils.get_download_link(version)

            version_dash = version.replace('.', '-') # Rename version number for filename compatibility

            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                download_file = (download_dir / version_dash).with_suffix('.tmp')  # Construct download file

                print(f"Downloading [{item}] version [{version}] to {download_file} ...")
                # Write response content to local file
                with open(download_file, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                download_file = download_file.rename((download_dir / version_dash).with_suffix('.zip'))  # .zip extension
                print(f"[{item}] version [{version}] download complete.")

                # Unzip file and delete archive
                print(f"Extracting {download_file} ...")
                with zipfile.ZipFile(download_file, 'r') as zip_item:
                    zip_item.extractall(download_dir / version_dash)
                download_file.unlink()
                print(f"Extraction complete.")

        return version_dash

    # TODO: last working version option, config update
    @staticmethod
    def browser_install_prompt():
        """Prompt the user for Chrome and chromedriver installation."""
        options = [1, 2, 3, 4, 5]
        choice = None

        # Browser install menu
        print('-' * (shutil.get_terminal_size().columns - 1))  # Horizontal line (cosmetic)
        print("Setup/Install for Chrome and chromedriver:\n"
              "If a channel is selected, the latest version for the selected channel will be installed.\n\n"
              "Select a channel/version to install:\n"
              "1. Stable (recommended)\n"
              "2. Beta\n"
              "3. Dev\n"
              "4. Canary\n"
              "5. Specific Version (not currently supported)")  # TODO: specific version support
        print('-' * (shutil.get_terminal_size().columns - 1))

        while choice not in options:
            choice = int(input("Input: "))

        user_platform = SetupUtils.get_platform()
        match choice:
            case 1: curr_version = SetupUtils.download_browser_items(channel='Stable', user_platform=user_platform)
            case 2: curr_version = SetupUtils.download_browser_items(channel='Beta', user_platform=user_platform)
            case 3: curr_version = SetupUtils.download_browser_items(channel='Dev', user_platform=user_platform)
            case 4: curr_version = SetupUtils.download_browser_items(channel='Canary', user_platform=user_platform)
            case 5: pass  # TODO: specific version support


if __name__ == '__main__':
    SetupUtils.browser_install_prompt()
