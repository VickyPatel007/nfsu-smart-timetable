"""Security utilities for the Smart Timetable Generator.

Secure coding practices implemented:
1. CSRF Protection - Token-based via Flask-WTF
2. Input Validation - Length limits, type checking, sanitization
3. XSS Prevention - Jinja2 auto-escaping + bleach sanitization  
4. SQL Injection Prevention - No raw SQL, using JSON file storage
5. Content Security Policy - Restrictive CSP headers
6. Secure Headers - X-Frame-Options, X-Content-Type-Options, etc.
7. Rate Limiting - Simple in-memory rate limiter
8. Error Handling - No information leakage in error responses
9. Input Length Limits - Prevent DoS via oversized inputs
10. Atomic File Writes - Prevent data corruption
"""
import html
import re
import time
import secrets
import functools
from collections import defaultdict
from flask import request, abort, jsonify, g
import bleach

# --- Input Validation ---

MAX_STRING_LENGTH = 200
MAX_NAME_LENGTH = 100
MAX_CODE_LENGTH = 20
MAX_ITEMS_PER_COLLECTION = 500
TIME_PATTERN = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')
DAYS_OF_WEEK = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'}

def sanitize_string(value: str, max_length: int = MAX_STRING_LENGTH) -> str:
    """Sanitize a string input: strip, limit length, remove HTML."""
    if not isinstance(value, str):
        raise ValueError('Expected string value')
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f'Value exceeds maximum length of {max_length} characters')
    # Remove any HTML tags
    value = bleach.clean(value, tags=[], strip=True)
    return value

def validate_time(time_str: str) -> str:
    """Validate HH:MM format."""
    if not isinstance(time_str, str):
        raise ValueError('Time must be a string')
    time_str = time_str.strip()
    if not TIME_PATTERN.match(time_str):
        raise ValueError(f'Invalid time format: {time_str}. Use HH:MM (24-hour).')
    return time_str

def validate_day(day: str) -> str:
    """Validate day of week."""
    day = sanitize_string(day, 20)
    if day not in DAYS_OF_WEEK:
        raise ValueError(f'Invalid day: {day}')
    return day

def validate_positive_int(value, field_name: str = 'value', max_val: int = 10000) -> int:
    """Validate positive integer."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} must be a positive integer')
    if value < 0 or value > max_val:
        raise ValueError(f'{field_name} must be between 0 and {max_val}')
    return value

def validate_id(value: str) -> str:
    """Validate UUID-format ID to prevent injection."""
    if not isinstance(value, str):
        raise ValueError('ID must be a string')
    # Allow UUID format or simple alphanumeric IDs
    if not re.match(r'^[a-zA-Z0-9\-_]{1,50}$', value):
        raise ValueError('Invalid ID format')
    return value

# --- Security Headers ---

def add_security_headers(response):
    """Add security headers to every response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    # CSP - allow inline styles/scripts for simplicity, but restrict sources
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    return response

# --- Rate Limiting ---

class RateLimiter:
    """Simple in-memory rate limiter."""
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        now = time.time()
        # Clean old entries
        self.requests[key] = [t for t in self.requests[key] if now - t < self.window]
        if len(self.requests[key]) >= self.max_requests:
            return False
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter(max_requests=120, window_seconds=60)

def check_rate_limit():
    """Check rate limit before processing request."""
    client_ip = request.remote_addr or 'unknown'
    if not rate_limiter.is_allowed(client_ip):
        abort(429)

# --- Request Validation ---

def get_json_body(max_size: int = 1024 * 100) -> dict:
    """Safely get JSON body from request with size limit."""
    if request.content_length and request.content_length > max_size:
        raise ValueError('Request body too large')
    data = request.get_json(silent=True)
    if data is None:
        raise ValueError('Invalid or missing JSON body')
    if not isinstance(data, dict):
        raise ValueError('JSON body must be an object')
    return data
