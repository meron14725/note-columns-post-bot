#!/usr/bin/env python
"""Test API without XSRF token."""

import sys
from pathlib import Path
import requests
import json
from urllib.parse import quote

# Import modules using installed package structure

def test_api_without_token():
    """Test note API without XSRF token."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Sec-Ch-Ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    })
    
    # First get the page to establish session
    print("Getting initial page...")
    response = session.get("https://note.com/interests/K-POP")
    print(f"Initial page status: {response.status_code}")
    
    # Extract client code
    import re
    ccd_match = re.search(r'ccd:\s*"([a-f0-9]{64})"', response.text)
    if not ccd_match:
        print("❌ Could not find client code")
        return
    
    client_code = ccd_match.group(1)
    print(f"✅ Found client code: {client_code[:10]}...")
    
    # Test different API approaches
    test_cases = [
        {
            "name": "With client code only",
            "headers": {
                "X-Note-Client-Code": client_code,
                "Referer": "https://note.com/interests/K-POP",
            }
        },
        {
            "name": "Without any special headers",
            "headers": {
                "Referer": "https://note.com/interests/K-POP",
            }
        },
        {
            "name": "With empty XSRF token",
            "headers": {
                "X-Note-Client-Code": client_code,
                "X-Xsrf-Token": "",
                "Referer": "https://note.com/interests/K-POP",
            }
        },
    ]
    
    label_name = "K-POP"
    api_url = f"https://note.com/api/v3/mkit_layouts/json?context=top_keyword&page=1&args[label_name]={quote(label_name)}"
    
    for test_case in test_cases:
        print(f"\n=== {test_case['name']} ===")
        
        test_headers = {**session.headers, **test_case['headers']}
        
        try:
            response = session.get(api_url, headers=test_headers)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ Success! Response contains {len(str(data))} characters")
                    
                    # Check if we have actual data
                    sections = data.get('data', {}).get('sections', [])
                    total_articles = 0
                    for section in sections:
                        total_articles += len(section.get('notes', []))
                    
                    print(f"Found {total_articles} articles in response")
                    
                    if total_articles > 0:
                        print("🎉 API call successful!")
                        # Show first article
                        first_note = sections[0]['notes'][0] if sections and sections[0].get('notes') else None
                        if first_note:
                            print(f"First article: {first_note.get('name', 'No title')}")
                        return True
                    
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON response")
                    print(f"Response text: {response.text[:200]}...")
            else:
                print(f"❌ Failed with status {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print("\n❌ All test cases failed")
    return False

if __name__ == "__main__":
    test_api_without_token()