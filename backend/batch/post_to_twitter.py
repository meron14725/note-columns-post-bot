"""Twitter posting batch script."""

import asyncio
import sys
# Import modules using installed package structure

from backend.app.services.twitter_bot import TwitterBot
from backend.app.utils.logger import setup_logger, get_logger
from config.config import config

logger = setup_logger("twitter_batch", console=True)


async def main():
    """Main function for Twitter posting."""
    logger.info("Starting Twitter posting batch")
    
    try:
        # Validate configuration
        if not config.has_twitter_credentials:
            logger.error("Twitter credentials not configured")
            sys.exit(1)
        
        # Initialize Twitter bot
        bot = TwitterBot()
        
        # Run scheduled posting
        success = await bot.post_scheduled_content()
        
        if success:
            logger.info("Twitter posting batch completed successfully")
            sys.exit(0)
        else:
            logger.error("Twitter posting batch failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Twitter posting batch interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in Twitter posting batch: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())