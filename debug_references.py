#!/usr/bin/env python3
"""Debug article reference retrieval."""

import sys
from pathlib import Path

# Add the parent directory to sys.path for imports
sys.path.append(str(Path(__file__).parent))

from backend.app.repositories.article_reference_repository import ArticleReferenceRepository
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)

def test_get_unprocessed():
    """Test getting unprocessed article references."""
    repo = ArticleReferenceRepository()
    
    # Get all references
    try:
        references = repo.get_unprocessed_references()
        print(f"Found {len(references)} unprocessed references")
        
        if references:
            print("First 3 references:")
            for i, ref in enumerate(references[:3]):
                print(f"  {i+1}. {ref.key}/{ref.urlname} - {ref.category} - {ref.title[:50]}...")
        else:
            print("No unprocessed references found")
            
        # Check total count
        total_count = repo.get_total_reference_count()
        print(f"Total references in database: {total_count}")
        
        # Check category counts
        category_counts = repo.get_reference_counts_by_category()
        print("Category distribution:")
        for category, count in category_counts.items():
            print(f"  {category}: {count}")
            
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Failed to get references: {e}")

if __name__ == "__main__":
    test_get_unprocessed()