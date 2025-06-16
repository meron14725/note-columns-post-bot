#!/usr/bin/env python
"""Debug script for article detail fetch."""

import sys
from pathlib import Path
import json
import re
from bs4 import BeautifulSoup

# Import modules using installed package structure

from backend.app.services.scraper import NoteScraper
from backend.app.utils.logger import setup_logger

logger = setup_logger("debug_detail", console=True)

async def debug_article_detail():
    """Debug article detail fetching process."""
    
    async with NoteScraper() as scraper:
        # First get article list
        logger.info("=== Getting article list ===")
        article_list = await scraper.collect_article_list()
        
        if not article_list:
            logger.error("No articles found")
            return
        
        # Take the first article for debugging
        ref = article_list[0]
        logger.info(f"Selected article for debugging:")
        logger.info(f"  Title: {ref['title']}")
        logger.info(f"  Author: {ref['author']}")
        logger.info(f"  Key: {ref['key']}")
        logger.info(f"  Urlname: {ref['urlname']}")
        logger.info(f"  URL: {ref['url']}")
        
        # Debug the detail fetching process
        urlname = ref['urlname']
        key = ref['key']
        article_url = f"https://note.com/{urlname}/n/{key}"
        
        logger.info(f"\n=== Fetching article detail ===")
        logger.info(f"Article URL: {article_url}")
        
        # Get session tokens first
        if not scraper.client_code:
            logger.info("Getting session tokens...")
            base_url = f"https://note.com/{urlname}"
            success = scraper._get_session_tokens(base_url)
            logger.info(f"Token acquisition: {'SUCCESS' if success else 'FAILED'}")
            if success:
                logger.info(f"Client code: {scraper.client_code[:20]}...")
                logger.info(f"XSRF token: {scraper.xsrf_token[:20] if scraper.xsrf_token else 'None'}")
        
        # Make the detail request
        logger.info(f"\n=== Making detail request ===")
        
        headers = {
            **scraper.session.headers,
            "Referer": f"https://note.com/{urlname}",
        }
        
        response = scraper.session.get(article_url, headers=headers)
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response URL: {response.url}")
        logger.info(f"Response headers:")
        for key, value in response.headers.items():
            logger.info(f"  {key}: {value}")
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch article: {response.status_code}")
            logger.error(f"Response text: {response.text[:500]}...")
            return
        
        html = response.text
        logger.info(f"HTML length: {len(html)}")
        
        # Check for different JavaScript data patterns
        logger.info(f"\n=== Analyzing HTML content ===")
        
        # Look for different JS data patterns
        js_patterns = [
            ('__INITIAL_STATE__', 'window.__INITIAL_STATE__'),
            ('__NUXT__', 'window.__NUXT__'),
            ('__NEXT_DATA__', '__NEXT_DATA__'),
            ('noteData', 'noteData'),
            ('initialProps', 'initialProps'),
        ]
        
        found_js_data = []
        for pattern_name, pattern in js_patterns:
            if pattern in html:
                found_js_data.append((pattern_name, pattern))
                logger.info(f"✅ Found {pattern_name}")
            else:
                logger.info(f"❌ No {pattern_name}")
        
        if 'window.__INITIAL_STATE__' in html:
            logger.info("✅ Found __INITIAL_STATE__")
            
            # Extract __INITIAL_STATE__
            try:
                start = html.find('window.__INITIAL_STATE__') + len('window.__INITIAL_STATE__ = ')
                end = html.find('</script>', start)
                json_str = html[start:end].rstrip(';').strip()
                
                logger.info(f"JSON string length: {len(json_str)}")
                logger.info(f"JSON string preview: {json_str[:200]}...")
                
                data = json.loads(json_str)
                logger.info(f"Successfully parsed JSON with {len(data)} top-level keys")
                logger.info(f"Top-level keys: {list(data.keys())}")
                
                # Look for note data in different locations
                logger.info(f"\n=== Searching for note data ===")
                
                note_locations = [
                    ('data.note', data.get('note')),
                    ('data.notes', data.get('notes')),
                    ('data.currentNote', data.get('currentNote')),
                ]
                
                if 'notes' in data and isinstance(data['notes'], dict):
                    for note_key in list(data['notes'].keys())[:3]:  # Check first 3 notes
                        note_locations.append((f'data.notes[{note_key}]', data['notes'][note_key]))
                
                found_note = None
                for location_name, note_data in note_locations:
                    if note_data:
                        logger.info(f"✅ Found note at {location_name}")
                        logger.info(f"   Note keys: {list(note_data.keys()) if isinstance(note_data, dict) else 'Not a dict'}")
                        
                        if isinstance(note_data, dict):
                            logger.info(f"   ID: {note_data.get('id', 'N/A')}")
                            logger.info(f"   Name: {note_data.get('name', 'N/A')}")
                            logger.info(f"   User: {note_data.get('user', {}).get('nickname', 'N/A') if note_data.get('user') else 'N/A'}")
                            
                            # Check if this is the right note by comparing key
                            note_id = str(note_data.get('id', ''))
                            if note_id == ref['key'] or note_id == ref['id']:
                                logger.info(f"🎯 This matches our target article!")
                                found_note = note_data
                                break
                    else:
                        logger.info(f"❌ No note at {location_name}")
                
                if not found_note:
                    logger.warning("Could not find matching note in __INITIAL_STATE__")
                    logger.info("Trying to find any note with the matching key...")
                    
                    # Deep search for the key
                    def find_key_in_data(obj, target_key, path=""):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                new_path = f"{path}.{k}" if path else k
                                if k == 'id' and str(v) == target_key:
                                    logger.info(f"Found matching ID at path: {path}")
                                    return obj
                                elif k == 'key' and str(v) == target_key:
                                    logger.info(f"Found matching key at path: {path}")
                                    return obj
                                result = find_key_in_data(v, target_key, new_path)
                                if result:
                                    return result
                        elif isinstance(obj, list):
                            for i, item in enumerate(obj):
                                result = find_key_in_data(item, target_key, f"{path}[{i}]")
                                if result:
                                    return result
                        return None
                    
                    found_note = find_key_in_data(data, ref['key'])
                    if not found_note:
                        found_note = find_key_in_data(data, ref['id'])
                
                if found_note:
                    logger.info(f"\n=== Found note data ===")
                    logger.info(f"Note data: {json.dumps(found_note, indent=2, ensure_ascii=False)[:1000]}...")
                else:
                    logger.warning("Could not find note data anywhere in __INITIAL_STATE__")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse __INITIAL_STATE__ JSON: {e}")
            except Exception as e:
                logger.error(f"Error analyzing __INITIAL_STATE__: {e}")
        
        # Try other JavaScript data sources
        for pattern_name, pattern in found_js_data:
            if pattern_name == '__INITIAL_STATE__':
                continue  # Already processed above
                
            logger.info(f"\n=== Analyzing {pattern_name} ===")
            try:
                if pattern_name == '__NUXT__':
                    # Extract __NUXT__ data
                    start = html.find('window.__NUXT__=') + len('window.__NUXT__=')
                    end = html.find(';</script>', start)
                    if end == -1:
                        end = html.find('\n', start)
                    json_str = html[start:end].strip()
                    
                    logger.info(f"NUXT JSON string length: {len(json_str)}")
                    logger.info(f"NUXT JSON preview: {json_str[:200]}...")
                    
                    # Try to parse (NUXT data is often complex)
                    if json_str.startswith('(function('):
                        logger.info("NUXT data is a function, extracting parameters...")
                        # Extract the data structure from function parameters
                        func_match = re.search(r'\(function\([^)]+\)\{return ({.+})\}\(', json_str)
                        if func_match:
                            data_str = func_match.group(1)
                            logger.info(f"Extracted data: {data_str[:200]}...")
                            # This is still complex to parse, but we can look for specific patterns
                        
                elif pattern_name == '__NEXT_DATA__':
                    # Extract Next.js data
                    script_match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>([^<]+)</script>', html)
                    if script_match:
                        json_str = script_match.group(1)
                        data = json.loads(json_str)
                        logger.info(f"NEXT_DATA keys: {list(data.keys())}")
                        
            except Exception as e:
                logger.error(f"Error analyzing {pattern_name}: {e}")
        
        if not found_js_data:
            logger.warning("❌ No JavaScript data structures found")
        
        # Fallback: HTML parsing
        logger.info(f"\n=== HTML parsing fallback ===")
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for title
        title_candidates = [
            soup.find('h1'),
            soup.find('title'),
            soup.find('meta', {'property': 'og:title'}),
            soup.find('meta', {'name': 'twitter:title'}),
        ]
        
        logger.info("Title candidates:")
        for i, candidate in enumerate(title_candidates):
            if candidate:
                if candidate.name == 'meta':
                    title_text = candidate.get('content', '')
                else:
                    title_text = candidate.get_text(strip=True)
                logger.info(f"  {i+1}. {candidate.name}: {title_text[:100]}...")
            else:
                logger.info(f"  {i+1}. None")
        
        # Look for author
        author_candidates = [
            soup.find('meta', {'name': 'author'}),
            soup.find('meta', {'property': 'article:author'}),
            soup.find('meta', {'property': 'og:author'}),
        ]
        
        logger.info("Author candidates:")
        for i, candidate in enumerate(author_candidates):
            if candidate:
                author_text = candidate.get('content', '')
                logger.info(f"  {i+1}. {candidate.get('name') or candidate.get('property')}: {author_text}")
            else:
                logger.info(f"  {i+1}. None")
        
        # Look for content
        content_candidates = [
            soup.find('div', class_=re.compile(r'note-common-styles__textnote-body')),
            soup.find('div', class_=re.compile(r'content')),
            soup.find('div', class_=re.compile(r'article-body')),
            soup.find('meta', {'name': 'description'}),
            soup.find('meta', {'property': 'og:description'}),
        ]
        
        logger.info("Content candidates:")
        for i, candidate in enumerate(content_candidates):
            if candidate:
                if candidate.name == 'meta':
                    content_text = candidate.get('content', '')
                else:
                    content_text = candidate.get_text(strip=True)
                logger.info(f"  {i+1}. {candidate.name}: {content_text[:100]}...")
            else:
                logger.info(f"  {i+1}. None")

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_article_detail())