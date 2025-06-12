"""Rate limiting utilities for API calls."""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass
from collections import defaultdict, deque


@dataclass
class RateLimit:
    """Rate limit configuration."""
    
    requests_per_minute: int
    requests_per_day: int
    requests_per_second: Optional[int] = None


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, rate_limit: RateLimit) -> None:
        """Initialize rate limiter.
        
        Args:
            rate_limit: Rate limit configuration
        """
        self.rate_limit = rate_limit
        self.request_times: deque = deque()
        self.daily_count = 0
        self.last_reset_date = time.strftime("%Y-%m-%d")
        self._lock = asyncio.Lock() if asyncio.iscoroutinefunction(self._wait_if_needed) else None
    
    def _reset_daily_counter_if_needed(self) -> None:
        """Reset daily counter if it's a new day."""
        current_date = time.strftime("%Y-%m-%d")
        if current_date != self.last_reset_date:
            self.daily_count = 0
            self.last_reset_date = current_date
    
    def _clean_old_requests(self) -> None:
        """Remove request times older than 1 minute."""
        current_time = time.time()
        while self.request_times and current_time - self.request_times[0] > 60:
            self.request_times.popleft()
    
    def _wait_if_needed(self) -> Optional[float]:
        """Calculate wait time if rate limit would be exceeded.
        
        Returns:
            Wait time in seconds, or None if no wait needed
        """
        self._reset_daily_counter_if_needed()
        self._clean_old_requests()
        
        current_time = time.time()
        
        # Check daily limit
        if self.daily_count >= self.rate_limit.requests_per_day:
            # Calculate seconds until next day
            tomorrow = time.strftime("%Y-%m-%d", time.localtime(current_time + 86400))
            tomorrow_timestamp = time.mktime(time.strptime(tomorrow, "%Y-%m-%d"))
            return tomorrow_timestamp - current_time
        
        # Check per-minute limit
        if len(self.request_times) >= self.rate_limit.requests_per_minute:
            # Wait until the oldest request is more than 1 minute old
            oldest_request = self.request_times[0]
            wait_time = 60 - (current_time - oldest_request)
            if wait_time > 0:
                return wait_time
        
        # Check per-second limit if configured
        if self.rate_limit.requests_per_second:
            recent_requests = sum(
                1 for req_time in self.request_times 
                if current_time - req_time < 1
            )
            if recent_requests >= self.rate_limit.requests_per_second:
                return 1.0
        
        return None
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded (synchronous)."""
        wait_time = self._wait_if_needed()
        if wait_time:
            time.sleep(wait_time)
    
    async def await_if_needed(self) -> None:
        """Wait if rate limit would be exceeded (asynchronous)."""
        async with self._lock:
            wait_time = self._wait_if_needed()
            if wait_time:
                await asyncio.sleep(wait_time)
    
    def record_request(self) -> None:
        """Record a request for rate limiting."""
        current_time = time.time()
        self.request_times.append(current_time)
        self.daily_count += 1
    
    def get_status(self) -> Dict[str, int]:
        """Get current rate limiting status.
        
        Returns:
            Dictionary with current status
        """
        self._reset_daily_counter_if_needed()
        self._clean_old_requests()
        
        return {
            "requests_this_minute": len(self.request_times),
            "requests_today": self.daily_count,
            "minute_limit": self.rate_limit.requests_per_minute,
            "daily_limit": self.rate_limit.requests_per_day,
        }
    
    def can_make_request(self) -> bool:
        """Check if a request can be made without waiting.
        
        Returns:
            True if request can be made immediately
        """
        return self._wait_if_needed() is None


class MultiServiceRateLimiter:
    """Rate limiter for multiple services."""
    
    def __init__(self) -> None:
        """Initialize multi-service rate limiter."""
        self.limiters: Dict[str, RateLimiter] = {}
    
    def add_service(self, service_name: str, rate_limit: RateLimit) -> None:
        """Add a service with its rate limit.
        
        Args:
            service_name: Name of the service
            rate_limit: Rate limit configuration
        """
        self.limiters[service_name] = RateLimiter(rate_limit)
    
    def wait_if_needed(self, service_name: str) -> None:
        """Wait if rate limit would be exceeded for a service.
        
        Args:
            service_name: Name of the service
        """
        if service_name in self.limiters:
            self.limiters[service_name].wait_if_needed()
    
    async def await_if_needed(self, service_name: str) -> None:
        """Wait if rate limit would be exceeded for a service (async).
        
        Args:
            service_name: Name of the service
        """
        if service_name in self.limiters:
            await self.limiters[service_name].await_if_needed()
    
    def record_request(self, service_name: str) -> None:
        """Record a request for a service.
        
        Args:
            service_name: Name of the service
        """
        if service_name in self.limiters:
            self.limiters[service_name].record_request()
    
    def get_status(self, service_name: str) -> Optional[Dict[str, int]]:
        """Get rate limiting status for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Status dictionary or None if service not found
        """
        if service_name in self.limiters:
            return self.limiters[service_name].get_status()
        return None
    
    def get_all_status(self) -> Dict[str, Dict[str, int]]:
        """Get rate limiting status for all services.
        
        Returns:
            Dictionary mapping service names to their status
        """
        return {
            service_name: limiter.get_status()
            for service_name, limiter in self.limiters.items()
        }


# Global rate limiter instance
rate_limiter = MultiServiceRateLimiter()

# Add common services
rate_limiter.add_service("groq", RateLimit(
    requests_per_minute=30,
    requests_per_day=14400
))

rate_limiter.add_service("note", RateLimit(
    requests_per_minute=60,
    requests_per_day=5000,
    requests_per_second=2
))

rate_limiter.add_service("twitter", RateLimit(
    requests_per_minute=300,
    requests_per_day=2000
))