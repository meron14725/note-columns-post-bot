"""Content quality checking utilities."""

import re
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)


class ContentQualityChecker:
    """Checks content quality and applies exclusion rules."""
    
    def __init__(self):
        """Initialize the content quality checker."""
        # Pattern to match note.com URLs
        self.note_url_pattern = re.compile(
            r'https?://note\.com/[\w\-_]+/n/[\w\-_]+',
            re.IGNORECASE
        )
    
    def check_note_link_spam(self, content: str, threshold: int = 4) -> Tuple[bool, int, str]:
        """Check if content contains excessive note.com links.
        
        Args:
            content: Article content to check
            threshold: Maximum allowed note.com links (default: 4)
            
        Returns:
            Tuple of (should_exclude, link_count, exclusion_reason)
        """
        if not content:
            return False, 0, ""
        
        # Find all note.com links in the content
        note_links = self.note_url_pattern.findall(content)
        link_count = len(note_links)
        
        logger.debug(f"Found {link_count} note.com links in content")
        
        if link_count >= threshold:
            exclusion_reason = f"note.comリンクが{link_count}個含まれており、品質基準（{threshold}個未満）を満たしません"
            logger.info(f"Content excluded due to excessive note.com links: {link_count} >= {threshold}")
            return True, link_count, exclusion_reason
        
        return False, link_count, ""
    
    def get_note_links(self, content: str) -> List[str]:
        """Extract all note.com links from content.
        
        Args:
            content: Article content to extract links from
            
        Returns:
            List of found note.com URLs
        """
        if not content:
            return []
        
        return self.note_url_pattern.findall(content)
    
    def check_content_quality(self, content: str, title: str = "") -> Tuple[bool, str]:
        """Perform comprehensive content quality check.
        
        Args:
            content: Article content to check
            title: Article title (optional)
            
        Returns:
            Tuple of (should_exclude, exclusion_reason)
        """
        if not content:
            return True, "記事内容が空です"
        
        # Check for excessive note.com links
        should_exclude, link_count, link_reason = self.check_note_link_spam(content)
        if should_exclude:
            return True, link_reason
        
        # Additional quality checks can be added here
        # For example:
        # - Minimum content length
        # - Spam detection
        # - Language detection
        
        return False, ""