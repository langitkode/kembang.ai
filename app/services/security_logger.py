"""Security event logging for audit trail."""

import logging
from typing import Optional
from datetime import datetime

# Create dedicated security logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

# Add file handler for security events (in production)
# In development, just use console
if not security_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [SECURITY] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    security_logger.addHandler(console_handler)


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
    success: bool = True,
):
    """
    Log a security-relevant event.
    
    Args:
        event_type: Type of event (e.g., "LOGIN_ATTEMPT", "PASSWORD_CHANGE")
        user_id: User ID if available
        email: User email if available
        ip_address: Client IP address
        details: Additional event details
        success: Whether the action was successful
    """
    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "email": email,
        "ip_address": ip_address,
        "success": success,
        "timestamp": datetime.now().isoformat(),
    }
    
    if details:
        log_data.update(details)
    
    # Log with appropriate level
    if success:
        security_logger.info(f"{event_type}: {log_data}")
    else:
        security_logger.warning(f"{event_type}_FAILED: {log_data}")


# Convenience functions for common events

def log_login_attempt(
    email: str,
    success: bool,
    ip_address: Optional[str] = None,
    user_id: Optional[str] = None,
    reason: Optional[str] = None,
):
    """Log login attempt."""
    log_security_event(
        event_type="LOGIN_ATTEMPT",
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        details={"reason": reason} if reason else None,
        success=success,
    )


def log_account_locked(
    email: str,
    locked_until: datetime,
    ip_address: Optional[str] = None,
):
    """Log account lockout."""
    log_security_event(
        event_type="ACCOUNT_LOCKED",
        email=email,
        ip_address=ip_address,
        details={"locked_until": locked_until.isoformat()},
        success=False,
    )


def log_registration(
    email: str,
    user_id: str,
    ip_address: Optional[str] = None,
):
    """Log user registration."""
    log_security_event(
        event_type="USER_REGISTRATION",
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        success=True,
    )


def log_password_change(
    user_id: str,
    email: str,
    ip_address: Optional[str] = None,
):
    """Log password change."""
    log_security_event(
        event_type="PASSWORD_CHANGE",
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        success=True,
    )


def log_permission_denied(
    user_id: str,
    email: str,
    resource: str,
    ip_address: Optional[str] = None,
):
    """Log permission denied event."""
    log_security_event(
        event_type="PERMISSION_DENIED",
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        details={"resource": resource},
        success=False,
    )
