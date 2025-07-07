# encoding: utf-8
import random
import time
import hashlib
from datetime import datetime, timedelta
from flask import session
import ckan.plugins.toolkit as toolkit

import logging
log = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with simple math captcha for unauthenticated users."""
    
    def __init__(self):
        self.search_limit = toolkit.config.get('schemingdcat.search_rate_limit', 10)
        self.time_window = toolkit.config.get('schemingdcat.search_time_window', 300)  # 5 minutes
        self.captcha_required_after = toolkit.config.get('schemingdcat.captcha_after_searches', 10)
        
    def _get_session_key(self, prefix='search'):
        """Generate a session key for tracking."""
        return f'schemingdcat_{prefix}_tracking'
    
    def _get_client_identifier(self):
        """Get a unique identifier for the client (IP + User-Agent)."""
        from flask import request
        ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        user_agent = request.environ.get('HTTP_USER_AGENT', '')
        return hashlib.md5(f"{ip}:{user_agent}".encode()).hexdigest()
    
    def track_search(self):
        """Track a search request for the current session."""
        key = self._get_session_key()
        current_time = time.time()
        
        # Initialize or get existing tracking data
        if key not in session:
            session[key] = {
                'searches': [],
                'captcha_required': False,
                'captcha_failed_attempts': 0
            }
        
        tracking = session[key]
        
        # Remove old searches outside the time window
        tracking['searches'] = [
            timestamp for timestamp in tracking['searches']
            if current_time - timestamp < self.time_window
        ]
        
        # Add current search
        tracking['searches'].append(current_time)
        
        # Check if captcha should be required
        if len(tracking['searches']) >= self.captcha_required_after:
            tracking['captcha_required'] = True
        
        session[key] = tracking
        session.modified = True
        
        return tracking
    
    def is_rate_limited(self):
        """Check if the current session is rate limited."""
        key = self._get_session_key()
        
        if key not in session:
            return False
        
        tracking = session.get(key, {})
        current_time = time.time()
        
        # Count recent searches
        recent_searches = [
            timestamp for timestamp in tracking.get('searches', [])
            if current_time - timestamp < self.time_window
        ]
        
        # Check if rate limit exceeded
        if len(recent_searches) > self.search_limit:
            # Check if captcha is required and not solved
            if tracking.get('captcha_required', False):
                return True
        
        return False
    
    def needs_captcha(self):
        """Check if captcha is required for current session."""
        key = self._get_session_key()
        tracking = session.get(key, {})
        return tracking.get('captcha_required', False)
    
    def generate_captcha(self):
        """Generate a simple math captcha."""
        operations = [
            ('+', lambda a, b: a + b),
            ('-', lambda a, b: a - b),
            ('×', lambda a, b: a * b),
        ]
        
        # Generate two random numbers
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        
        # For subtraction, ensure positive result
        if num2 > num1:
            num1, num2 = num2, num1
        
        # Select random operation
        op_symbol, op_func = random.choice(operations)
        
        # Calculate answer
        answer = op_func(num1, num2)
        
        # Store in session
        captcha_key = self._get_session_key('captcha')
        session[captcha_key] = {
            'answer': str(answer),
            'generated_at': time.time(),
            'question': f"{num1} {op_symbol} {num2}"
        }
        session.modified = True
        
        return f"{num1} {op_symbol} {num2}"
    
    def verify_captcha(self, user_answer):
        """Verify the captcha answer."""
        captcha_key = self._get_session_key('captcha')
        captcha_data = session.get(captcha_key, {})
        
        if not captcha_data:
            return False
        
        # Check if captcha is expired (5 minutes)
        if time.time() - captcha_data.get('generated_at', 0) > 300:
            return False
        
        # Verify answer
        correct_answer = captcha_data.get('answer', '')
        is_correct = str(user_answer).strip() == correct_answer
        
        if is_correct:
            # Reset captcha requirement
            search_key = self._get_session_key()
            if search_key in session:
                session[search_key]['captcha_required'] = False
                session[search_key]['captcha_failed_attempts'] = 0
                # Clear some old searches to give user more headroom
                session[search_key]['searches'] = session[search_key]['searches'][-5:]
                session.modified = True
            
            # Clear captcha from session
            if captcha_key in session:
                del session[captcha_key]
                session.modified = True
        else:
            # Track failed attempts
            search_key = self._get_session_key()
            if search_key in session:
                session[search_key]['captcha_failed_attempts'] = \
                    session[search_key].get('captcha_failed_attempts', 0) + 1
                session.modified = True
        
        return is_correct
    
    def get_remaining_searches(self):
        """Get the number of searches remaining before captcha is required."""
        key = self._get_session_key()
        tracking = session.get(key, {})
        current_searches = len(tracking.get('searches', []))
        
        if current_searches >= self.captcha_required_after:
            return 0
        
        return self.captcha_required_after - current_searches
    
    def reset_session(self):
        """Reset rate limiting for current session (for testing)."""
        for key in [self._get_session_key(), self._get_session_key('captcha')]:
            if key in session:
                del session[key]
        session.modified = True


# Global instance
rate_limiter = RateLimiter()