"""Exception classes for the Usage Tracking SDK"""


class UsageTrackingError(Exception):
    """Base exception for usage tracking errors"""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response or {}


class RateLimitError(UsageTrackingError):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str, retry_after: int = None, response: dict = None):
        super().__init__(message, status_code=429, response=response)
        self.retry_after = retry_after


class ValidationError(UsageTrackingError):
    """Raised when event data validation fails"""
    
    def __init__(self, message: str, field_errors: list = None, response: dict = None):
        super().__init__(message, status_code=400, response=response)
        self.field_errors = field_errors or []


class AuthenticationError(UsageTrackingError):
    """Raised when authentication fails"""
    
    def __init__(self, message: str, response: dict = None):
        super().__init__(message, status_code=401, response=response)


class ServiceUnavailableError(UsageTrackingError):
    """Raised when the service is unavailable"""
    
    def __init__(self, message: str, response: dict = None):
        super().__init__(message, status_code=503, response=response)


class ConfigurationError(UsageTrackingError):
    """Raised when SDK configuration is invalid"""
    
    def __init__(self, message: str):
        super().__init__(message)


class RetryableError(UsageTrackingError):
    """Raised for errors that can be retried"""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message, status_code, response)