#!/usr/bin/env python3
"""Debug detailed session token acquisition."""

import re
import requests
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)

def test_detailed_session_tokens():
    """Test session token acquisition from different Note.com pages."""
    
    # Test different types of URLs
    test_cases = [
        {
            "name": "Interest page (K-POP)",
            "url": "https://note.com/interests/K-POP"
        },
        {
            "name": "User profile page",
            "url": "https://note.com/cozy_rhino3849"
        },
        {
            "name": "Specific article page",
            "url": "https://note.com/cozy_rhino3849/n/nab5988434b64"
        },
        {
            "name": "Note homepage",
            "url": "https://note.com/"
        }
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
    
    for test_case in test_cases:
        print(f"\n=== {test_case['name']} ===")
        print(f"URL: {test_case['url']}")
        
        try:
            response = session.get(test_case['url'])
            print(f"Status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Failed to get page: {response.status_code}")
                continue
            
            html = response.text
            print(f"HTML length: {len(html)}")
            
            # Look for client code patterns
            patterns = [
                (r'ccd:\s*"([a-f0-9]{64})"', "ccd property"),
                (r'window\.__INITIAL_STATE__.*?"ccd":"([a-f0-9]{64})"', "__INITIAL_STATE__ ccd"),
                (r'"clientCode":"([a-f0-9]{64})"', "clientCode property"),
                (r'clientCode:\s*"([a-f0-9]{64})"', "clientCode key"),
                (r'"client_code":"([a-f0-9]{64})"', "client_code property"),
                (r'client_code:\s*"([a-f0-9]{64})"', "client_code key")
            ]
            
            found_code = False
            for pattern, description in patterns:
                match = re.search(pattern, html)
                if match:
                    client_code = match.group(1)
                    print(f"✓ Found client code ({description}): {client_code[:10]}...")
                    found_code = True
                    break
            
            if not found_code:
                print("✗ No client code found")
                # Look for any 64-character hex strings
                hex_matches = re.findall(r'[a-f0-9]{64}', html)
                if hex_matches:
                    print(f"Found {len(hex_matches)} potential 64-char hex strings:")
                    for match in set(hex_matches)[:3]:  # Show first 3 unique
                        print(f"  {match[:10]}...")
                        # Check if it appears in a likely context
                        context_search = re.search(rf'.{{0,50}}{re.escape(match)}.{{0,50}}', html)
                        if context_search:
                            context = context_search.group(0).replace('\\n', ' ').strip()
                            print(f"    Context: {context[:100]}...")
                else:
                    print("No 64-char hex strings found")
            
            # Check for different script structures
            if 'window.__INITIAL_STATE__' in html:
                print("✓ Found __INITIAL_STATE__")
            elif 'window.__NUXT__' in html:
                print("✓ Found __NUXT__")
            elif '<script' in html:
                script_count = html.count('<script')
                print(f"Found {script_count} script tags (no __INITIAL_STATE__ or __NUXT__)")
            else:
                print("✗ No script tags found")
            
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
    test_detailed_session_tokens()