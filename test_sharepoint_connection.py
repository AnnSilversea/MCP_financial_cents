import os
import json
import sys
import base64
from dotenv import load_dotenv
from sharepoint.sharepoint_provider import SharePointProvider

def _safe_b64decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("utf-8"))

def _decode_jwt_no_verify(token: str) -> dict:
    # Diagnostic only: DO NOT use for security decisions.
    parts = (token or "").split(".")
    if len(parts) < 2:
        return {}
    try:
        return json.loads(_safe_b64decode(parts[1]).decode("utf-8"))
    except Exception:
        return {}

def test_connection():
    # 1. Load environment variables từ file .env
    load_dotenv()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    
    print("--- Checking SharePoint connection ---")
    
    try:
        # 2. Initialize provider
        # Provider will automatically read the variables: TENANT_ID, CLIENT_ID, CLIENT_SECRET, ...
        provider = SharePointProvider()
        print(f"Initialized provider successfully for site: {provider.site_host}{provider.site_path}")

        # Diagnostics: inspect token claims (roles/aud/tid) to help debug 401/403
        token = provider._get_token()
        claims = _decode_jwt_no_verify(token)
        if claims:
            roles = claims.get("roles") or []
            scp = claims.get("scp")
            print("\n--- Token claims (diagnostic) ---")
            print(f"aud: {claims.get('aud')}")
            print(f"tid: {claims.get('tid')}")
            print(f"appid: {claims.get('appid')}")
            if roles:
                print(f"roles: {roles}")
            if scp:
                print(f"scp: {scp}")

        # 3. Checking access token and resolving Site/Drive
        print("Checking access token and resolving Site/Drive...")
        site_id, drive_id = provider._resolve_site_and_drive()
        
        print(f"Connection successful!")
        print(f"Site ID: {site_id}")
        print(f"Drive ID: {drive_id}")
        print(f"Drive Name: {provider.drive_name}")

        # 4. Try listing root folders to test actual permissions
        print("\nTrying to list root folders...")
        # Use 'root' as the default ID for the root folder in Graph API
        folders, files = provider.list_folder_children("root")
        
        print(f"Found {len(folders)} folders and {len(files)} files in the root folder.")
        
        if folders:
            print("Example of some folders:")
            for folder in folders[:5]:
                print(f" - {folder.name} (ID: {folder.id})")

    except RuntimeError as e:
        print(f"Configuration or authentication error: {e}")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")

if __name__ == "__main__":
    test_connection()
