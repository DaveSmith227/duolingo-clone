"""
Email Service

Service for sending emails including password reset, email verification,
and other transactional emails using SMTP configuration.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from app.core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service for sending transactional emails.
    
    Handles SMTP configuration, email templates, and sending functionality
    with proper error handling and logging.
    """
    
    def __init__(self):
        """Initialize email service with configuration."""
        self.settings = get_settings()
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate email configuration."""
        # In development, we can skip email validation
        if self.settings.is_development:
            logger.info("Email service initialized in development mode - emails will be logged only")
            return
        
        # In production, validate SMTP configuration
        required_settings = [
            'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not hasattr(self.settings, setting) or not getattr(self.settings, setting):
                missing_settings.append(setting)
        
        if missing_settings:
            logger.warning(f"Missing email configuration: {', '.join(missing_settings)}")
    
    async def send_password_reset_email(
        self,
        email: str,
        reset_token: str,
        user_name: str,
        ip_address: str = None
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            email: Recipient email address
            reset_token: Password reset token
            user_name: User's display name
            ip_address: IP address for security info
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Build reset URL
            reset_url = f"{self.settings.frontend_url}/auth/reset-password?token={reset_token}"
            
            # Email subject and content
            subject = "Reset Your Password - Duolingo Clone"
            
            # Create email template
            html_content = self._create_password_reset_template(
                user_name=user_name,
                reset_url=reset_url,
                ip_address=ip_address
            )
            
            text_content = f"""
Hi {user_name},

We received a request to reset your password for your Duolingo Clone account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour for your security.

If you didn't request this password reset, please ignore this email.

For security, this request was made from IP address: {ip_address or 'unknown'}

Best regards,
The Duolingo Clone Team
            """.strip()
            
            # Send email
            return await self._send_email(
                to_email=email,
                subject=subject,
                text_content=text_content,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False
    
    def _create_password_reset_template(
        self,
        user_name: str,
        reset_url: str,
        ip_address: str = None
    ) -> str:
        """Create HTML email template for password reset."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Your Password</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #58cc02; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background-color: #58cc02; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 20px; padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .security-info {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🦉 Reset Your Password</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    
                    <p>We received a request to reset your password for your Duolingo Clone account.</p>
                    
                    <p>Click the button below to reset your password:</p>
                    
                    <a href="{reset_url}" class="button">Reset Password</a>
                    
                    <p>This link will expire in <strong>1 hour</strong> for your security.</p>
                    
                    <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
                    
                    {f'<div class="security-info"><strong>Security Notice:</strong> This request was made from IP address: {ip_address}</div>' if ip_address else ''}
                </div>
                <div class="footer">
                    <p>This is an automated email from Duolingo Clone. Please do not reply to this email.</p>
                    <p>If you're having trouble clicking the reset button, copy and paste this URL into your browser:</p>
                    <p style="word-break: break-all;">{reset_url}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: str = None
    ) -> bool:
        """
        Send email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            text_content: Plain text content
            html_content: HTML content (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # In development mode, just log the email
            if self.settings.is_development:
                logger.info(f"[DEV MODE] Email to {to_email}: {subject}")
                logger.info(f"Content: {text_content[:200]}...")
                return True
            
            # Check if SMTP is configured
            if not hasattr(self.settings, 'smtp_host') or not self.settings.smtp_host:
                logger.warning("SMTP not configured - email not sent")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.settings.from_email
            msg['To'] = to_email
            
            # Add text content
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)
            
            # Add HTML content if provided
            if html_content:
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                if hasattr(self.settings, 'smtp_use_tls') and self.settings.smtp_use_tls:
                    server.starttls()
                
                if hasattr(self.settings, 'smtp_username') and self.settings.smtp_username:
                    server.login(self.settings.smtp_username, self.settings.smtp_password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False


# Global email service instance
_email_service = None


def get_email_service() -> EmailService:
    """
    Get email service instance.
    
    Returns the global email service instance with singleton pattern.
    """
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service