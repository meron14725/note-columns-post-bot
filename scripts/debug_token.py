#!/usr/bin/env python
"""Debug script to check token acquisition."""

import sys
from pathlib import Path
import requests
import re
from bs4 import BeautifulSoup

# Import modules using installed package structure

def debug_note_session():
    """Debug note session token acquisition."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Sec-Ch-Ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    })
    
    # Try different URLs
    urls_to_test = [
        "https://note.com/",
        "https://note.com/topics",
        "https://note.com/interests/K-POP"
    ]
    
    for url in urls_to_test:
        print(f"\n=== Testing URL: {url} ===")
        
        try:
            print("Making request...")
            response = session.get(url)
            print(f"Status code: {response.status_code}")
            
            print("\nCookies received:")
            for cookie in session.cookies:
                print(f"  {cookie.name}: {cookie.value[:50]}...")
            
            print(f"\nResponse headers:")
            for key, value in response.headers.items():
                if 'token' in key.lower() or 'csrf' in key.lower() or 'xsrf' in key.lower():
                    print(f"  {key}: {value}")
            
            html = response.text
            print(f"\nHTML length: {len(html)}")
            
            # Look for different token patterns
            print("\nSearching for tokens in HTML...")
            
            # XSRF-TOKEN patterns
            xsrf_patterns = [
                r'XSRF-TOKEN["\']:\s*["\']([^"\']+)["\']',
                r'xsrf_token["\']:\s*["\']([^"\']+)["\']',
                r'_token["\']:\s*["\']([^"\']+)["\']',
                r'csrf[_-]?token["\']:\s*["\']([^"\']+)["\']',
            ]
            
            for pattern in xsrf_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    print(f"  Found XSRF token with pattern {pattern}: {matches[0][:20]}...")
            
            # Client code patterns
            ccd_patterns = [
                r'ccd:\s*"([a-f0-9]{64})"',
                r'window\.__INITIAL_STATE__.*?"ccd":"([a-f0-9]{64})"',
                r'clientCode["\']:\s*["\']([a-f0-9]{64})["\']',
            ]
            
            for pattern in ccd_patterns:
                matches = re.findall(pattern, html)
                if matches:
                    print(f"  Found client code with pattern {pattern}: {matches[0][:20]}...")
            
            # Check meta tags
            soup = BeautifulSoup(html, 'html.parser')
            meta_tags = soup.find_all('meta')
            
            print(f"\nMeta tags with token/csrf:")
            for meta in meta_tags:
                name = meta.get('name', '')
                content = meta.get('content', '')
                if 'token' in name.lower() or 'csrf' in name.lower():
                    print(f"  {name}: {content[:50]}...")
            
            # Check if the page is redirecting or showing different content
            if "ログイン" in html or "login" in html.lower():
                print("\n⚠️  Page seems to require login")
            
            if response.url != url:
                print(f"\n⚠️  Redirected to: {response.url}")
                
            # Check for API availability
            if 'api/v3/mkit_layouts' in html or '__NUXT__' in html:
                print("✅ Page appears to be API-enabled")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    debug_note_session()