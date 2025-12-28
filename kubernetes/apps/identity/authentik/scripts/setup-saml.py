#!/usr/bin/env python3
"""
Synology DSM SAML SSO Automation Script
Automates the configuration of SAML SSO between Authentik and Synology DSM
"""
import requests
import os
import sys
import json
import urllib3
from typing import Dict, Any, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SynologyAPI:
    """Base class for Synology API interactions"""

    def __init__(self, host: str, port: str, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"https://{host}:{port}"
        self.sid = None
        self.syno_token = None

    def login(self) -> bool:
        """Authenticate with Synology DSM"""
        print(f"Logging in to {self.host}...")
        login_url = f"{self.base_url}/webapi/auth.cgi"
        login_params = {
            'api': 'SYNO.API.Auth',
            'version': '7',
            'method': 'login',
            'account': self.username,
            'passwd': self.password,
            'session': 'Core',
            'format': 'sid',
            'enable_syno_token': 'yes'
        }

        try:
            response = requests.get(login_url, params=login_params, verify=False, timeout=30)
            result = response.json()
        except Exception as e:
            print(f"ERROR: Failed to connect to Synology: {e}")
            return False

        if not result.get('success'):
            error_code = result.get('error', {}).get('code', 'unknown')
            print(f"ERROR: Login failed with error code: {error_code}")
            return False

        self.sid = result['data']['sid']
        self.syno_token = result['data'].get('synotoken', '')
        print(f"Login successful (SynoToken: {'present' if self.syno_token else 'missing'})")
        return True

    def logout(self):
        """Logout from Synology DSM"""
        if not self.sid:
            return

        logout_params = {
            'api': 'SYNO.API.Auth',
            'version': '7',
            'method': 'logout',
            'session': 'Core',
            '_sid': self.sid
        }
        try:
            requests.get(f"{self.base_url}/webapi/auth.cgi",
                        params=logout_params, verify=False, timeout=10)
            print("Logged out successfully")
        except Exception as e:
            print(f"WARNING: Failed to logout: {e}")

    def query_api(self, api_name: str) -> Optional[Dict]:
        """Query information about a specific API"""
        query_url = f"{self.base_url}/webapi/query.cgi"
        params = {
            'api': 'SYNO.API.Info',
            'version': '1',
            'method': 'query',
            'query': api_name
        }

        try:
            response = requests.get(query_url, params=params, verify=False, timeout=30)
            result = response.json()
            if result.get('success'):
                return result.get('data', {})
            return None
        except Exception as e:
            print(f"ERROR: Failed to query API info: {e}")
            return None

    def list_all_apis(self) -> Dict[str, Any]:
        """List all available APIs on the Synology DSM"""
        query_url = f"{self.base_url}/webapi/query.cgi"
        params = {
            'api': 'SYNO.API.Info',
            'version': '1',
            'method': 'query',
            'query': 'ALL'
        }

        try:
            response = requests.get(query_url, params=params, verify=False, timeout=30)
            result = response.json()
            if result.get('success'):
                return result.get('data', {})
            return {}
        except Exception as e:
            print(f"ERROR: Failed to list APIs: {e}")
            return {}

    def call_api(self, api: str, version: int, method: str,
                 params: Optional[Dict] = None,
                 data: Optional[Dict] = None,
                 files: Optional[Dict] = None,
                 use_post: bool = False) -> Dict:
        """Generic API call method"""
        url = f"{self.base_url}/webapi/entry.cgi"

        api_params = {
            'api': api,
            'version': str(version),
            'method': method,
            '_sid': self.sid
        }

        if params:
            api_params.update(params)

        headers = {}
        if self.syno_token:
            headers['X-SYNO-TOKEN'] = self.syno_token
            if use_post:
                api_params['SynoToken'] = self.syno_token

        try:
            if use_post:
                response = requests.post(url, params=api_params, data=data,
                                        files=files, headers=headers,
                                        verify=False, timeout=60)
            else:
                response = requests.get(url, params=api_params, headers=headers,
                                       verify=False, timeout=30)

            return response.json()
        except Exception as e:
            print(f"ERROR: API call failed: {e}")
            return {'success': False, 'error': {'code': -1}}


class AuthentikAPI:
    """Class for interacting with Authentik"""

    def __init__(self, base_url: str, provider_slug: str):
        self.base_url = base_url
        self.provider_slug = provider_slug

    def download_saml_metadata(self) -> Optional[str]:
        """Download SAML metadata from Authentik"""
        metadata_url = f"{self.base_url}/application/saml/{self.provider_slug}/metadata/"

        print(f"Downloading SAML metadata from {metadata_url}...")
        try:
            # Don't set Accept header to avoid 406 error
            response = requests.get(metadata_url, verify=True, timeout=30)

            if response.status_code == 200:
                print(f"Successfully downloaded metadata ({len(response.text)} bytes)")
                return response.text
            else:
                print(f"ERROR: Failed to download metadata, status code: {response.status_code}")
                return None
        except Exception as e:
            print(f"ERROR: Failed to download metadata: {e}")
            return None


def discover_sso_apis(synology: SynologyAPI):
    """Discover SSO-related APIs on Synology DSM"""
    print("\n" + "="*80)
    print("DISCOVERING SSO/SAML APIs")
    print("="*80)

    apis = synology.list_all_apis()

    sso_apis = {}
    search_terms = ['SSO', 'SAML', 'Auth', 'Directory', 'LDAP', 'Domain']

    for api_name, api_info in apis.items():
        for term in search_terms:
            if term.lower() in api_name.lower():
                sso_apis[api_name] = api_info
                break

    if sso_apis:
        print(f"\nFound {len(sso_apis)} potentially relevant APIs:")
        for api_name, api_info in sorted(sso_apis.items()):
            max_version = api_info.get('maxVersion', 'unknown')
            path = api_info.get('path', 'unknown')
            print(f"  - {api_name} (v{max_version}) @ {path}")
    else:
        print("No SSO/SAML-related APIs found")

    return sso_apis


def configure_saml_sso(synology: SynologyAPI, metadata_xml: str,
                       entity_id: str, acs_url: str) -> bool:
    """
    Attempt to configure SAML SSO on Synology DSM

    This function tries various API endpoints that might handle SAML configuration.
    Since the exact API is not documented, we'll try common patterns.
    """
    print("\n" + "="*80)
    print("CONFIGURING SAML SSO")
    print("="*80)

    print("\nChecking current SAML status...")
    status_result = synology.call_api('SYNO.Core.Directory.SSO.SAML.Status', 1, 'get')
    if status_result.get('success'):
        print(f"  Current SAML status: {status_result.get('data', {})}")
    else:
        print(f"  Could not get SAML status: error {status_result.get('error', {}).get('code')}")

    print("\nEnabling SSO service...")
    sso_enable_result = synology.call_api(
        'SYNO.Core.Directory.SSO',
        2,
        'set',
        data={'enable': 'yes'},
        use_post=True
    )
    if sso_enable_result.get('success'):
        print("  ✓ SSO service enabled!")
    else:
        error_code = sso_enable_result.get('error', {}).get('code', 'unknown')
        print(f"  Status: error {error_code} (may already be enabled)")

    print("\nUploading SAML metadata...")
    files = {'metadata': ('metadata.xml', metadata_xml, 'text/xml')}
    metadata_result = synology.call_api(
        'SYNO.Core.Directory.SSO.SAML.Metadata',
        1,
        'import',
        files=files,
        use_post=True
    )
    if metadata_result.get('success'):
        print("  ✓ Successfully uploaded SAML metadata!")
    else:
        error_code = metadata_result.get('error', {}).get('code', 'unknown')
        print(f"  ✗ Metadata upload failed with error code: {error_code}")
        return False

    print("\nEnabling SAML SSO...")
    saml_enable_result = synology.call_api(
        'SYNO.Core.Directory.SSO.SAML',
        1,
        'set',
        data={'enable': 'yes'},
        use_post=True
    )
    if saml_enable_result.get('success'):
        print("  ✓ SAML SSO enabled successfully!")
        return True
    else:
        error_code = saml_enable_result.get('error', {}).get('code', 'unknown')
        print(f"  ✗ SAML enable failed with error code: {error_code}")

    print("\nTrying alternative SAML enable parameters...")
    for params in [{'enable': '1'}, {'enable': 'true'}, {'enable': True}]:
        result = synology.call_api(
            'SYNO.Core.Directory.SSO.SAML',
            1,
            'set',
            data=params,
            use_post=True
        )
        if result.get('success'):
            print(f"  ✓ SAML SSO enabled with params: {params}!")
            return True

    print(f"\n  The metadata was uploaded successfully but automatic enable failed.")
    print(f"  You may need to manually enable SAML in the DSM UI:")
    print(f"  Control Panel → Domain/LDAP → SSO Client → SAML 2.0")
    return False


def main():
    """Main execution function"""
    # Load configuration from environment
    synology_host = os.environ.get('SYNOLOGY_HOST')
    synology_port = os.environ.get('SYNOLOGY_PORT', '5001')
    synology_username = os.environ.get('SYNOLOGY_USERNAME')
    synology_password = os.environ.get('SYNOLOGY_PASSWORD')

    authentik_url = os.environ.get('AUTHENTIK_URL', 'https://auth.techvomit.xyz')
    authentik_provider_slug = os.environ.get('AUTHENTIK_PROVIDER_SLUG', 'synology-nas')

    nas_entity_id = os.environ.get('NAS_ENTITY_ID', 'https://nas.techvomit.xyz')
    nas_acs_url = os.environ.get('NAS_ACS_URL',
                                   'https://nas.techvomit.xyz/webman/3rdparty/SAML/acs.php')

    if not all([synology_host, synology_username, synology_password]):
        print("ERROR: Missing required environment variables")
        print("Required: SYNOLOGY_HOST, SYNOLOGY_USERNAME, SYNOLOGY_PASSWORD")
        sys.exit(1)

    print("="*80)
    print("SYNOLOGY DSM SAML SSO AUTOMATION")
    print("="*80)
    print(f"Synology: https://{synology_host}:{synology_port}")
    print(f"Authentik: {authentik_url}")
    print(f"Provider: {authentik_provider_slug}")
    print("="*80)

    authentik = AuthentikAPI(authentik_url, authentik_provider_slug)
    metadata_xml = authentik.download_saml_metadata()

    if not metadata_xml:
        print("ERROR: Failed to download Authentik metadata")
        sys.exit(1)

    # Save metadata to file for manual use if needed
    metadata_file = '/tmp/authentik-saml-metadata.xml'
    try:
        with open(metadata_file, 'w') as f:
            f.write(metadata_xml)
        print(f"✓ Metadata saved to: {metadata_file}")
    except Exception as e:
        print(f"WARNING: Failed to save metadata file: {e}")

    synology = SynologyAPI(synology_host, synology_port,
                           synology_username, synology_password)

    if not synology.login():
        sys.exit(1)

    try:
        sso_apis = discover_sso_apis(synology)

        success = configure_saml_sso(synology, metadata_xml,
                                     nas_entity_id, nas_acs_url)

        if success:
            print("\n" + "="*80)
            print("✓ SAML SSO CONFIGURATION COMPLETED SUCCESSFULLY!")
            print("="*80)
            print("\nNext steps:")
            print("1. Test SSO login in an incognito window")
            print("2. Verify user group mappings")
            print("3. Configure auto-provisioning if desired")
        else:
            print("\n" + "="*80)
            print("⚠ AUTOMATIC CONFIGURATION NOT AVAILABLE")
            print("="*80)
            print("\nThe SAML configuration API could not be found or is not accessible.")
            print("Please configure SAML SSO manually using the downloaded metadata:")
            print(f"\n  Metadata file: {metadata_file}")
            print(f"  Entity ID: {nas_entity_id}")
            print(f"  ACS URL: {nas_acs_url}")
            print("\nManual steps:")
            print("1. Log into DSM: https://nas.techvomit.xyz")
            print("2. Control Panel → Domain/LDAP → SSO Client → SAML 2.0")
            print("3. Enable SAML SSO and upload the metadata XML")
            print("4. Configure entity ID and ACS URL")
            print("5. Test in an incognito window")

            # Exit with code 2 to indicate manual intervention needed
            sys.exit(2)

    finally:
        synology.logout()


if __name__ == '__main__':
    main()
