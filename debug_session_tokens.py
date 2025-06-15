#!/usr/bin/env python3
"""Debug session token acquisition."""

import re
import requests
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)

def test_session_token_acquisition():
    """Test session token acquisition from Note.com."""
    # Test URLs
    test_urls = [
        "https://note.com/interests/K-POP",
        "https://note.com/interests/%E3%82%A2%E3%83%8B%E3%83%A1",
        "https://note.com/",
        "https://note.com/trending"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    })
    
    for url in test_urls:
        print(f"\n=== Testing {url} ===")
        try:
            response = session.get(url)
            print(f"Status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Failed to get page: {response.status_code}")
                continue
            
            html = response.text
            print(f"HTML length: {len(html)}")
            
            # Look for different patterns of client code
            patterns = [
                r'ccd:\s*"([a-f0-9]{64})"',
                r'window\.__INITIAL_STATE__.*?"ccd":"([a-f0-9]{64})"',
                r'"clientCode":"([a-f0-9]{64})"',
                r'clientCode:\s*"([a-f0-9]{64})"',
                r'"client_code":"([a-f0-9]{64})"',
                r'client_code:\s*"([a-f0-9]{64})"'
            ]
            
            found_code = False
            for i, pattern in enumerate(patterns):
                match = re.search(pattern, html)
                if match:
                    client_code = match.group(1)
                    print(f"✓ Found client code with pattern {i+1}: {client_code[:10]}...")
                    found_code = True
                    break
            
            if not found_code:
                print("✗ No client code found")
                # Look for any hex strings that might be the client code
                hex_matches = re.findall(r'"([a-f0-9]{64})"', html)
                if hex_matches:
                    print(f"Found {len(hex_matches)} potential 64-char hex strings:")
                    for match in hex_matches[:3]:  # Show first 3
                        print(f"  {match[:10]}...")
                else:
                    print("No 64-char hex strings found")
            
            # Check for __INITIAL_STATE__
            if 'window.__INITIAL_STATE__' in html:
                print("✓ Found __INITIAL_STATE__")
            else:
                print("✗ No __INITIAL_STATE__ found")
            
            # Check for XSRF token in cookies
            xsrf_token = None
            for cookie in session.cookies:
                if cookie.name == 'XSRF-TOKEN':
                    xsrf_token = cookie.value
                    print(f"✓ Found XSRF token: {xsrf_token[:10]}...")
                    break
            
            if not xsrf_token:
                print("✗ No XSRF token found")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_session_token_acquisition()