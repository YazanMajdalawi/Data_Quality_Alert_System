"""Configuration management for database connections and email settings."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class DatabaseConfig:
    """Database configuration for Magento and ERP."""
    
    @staticmethod
    def get_magento_config():
        """Get Magento database configuration."""
        return {
            'host': os.getenv('MAGENTO_DB_HOST', 'localhost'),
            'port': int(os.getenv('MAGENTO_DB_PORT', 3306)),
            'user': os.getenv('MAGENTO_DB_USER', ''),
            'password': os.getenv('MAGENTO_DB_PASSWORD', ''),
            'database': os.getenv('MAGENTO_DB_NAME', ''),
        }
    
    @staticmethod
    def get_erp_config():
        """Get ERP database configuration."""
        return {
            'host': os.getenv('ERP_DB_HOST', 'localhost'),
            'port': int(os.getenv('ERP_DB_PORT', 3306)),
            'user': os.getenv('ERP_DB_USER', ''),
            'password': os.getenv('ERP_DB_PASSWORD', ''),
            'database': os.getenv('ERP_DB_NAME', ''),
        }


class EmailConfig:
    """Email configuration for sending alerts via Microsoft Graph API."""
    
    @staticmethod
    def get_config():
        """Get email configuration."""
        recipients = os.getenv('EMAIL_RECIPIENTS', '')
        recipients_list = [r.strip() for r in recipients.split(',')] if recipients else []
        
        return {
            'client_id': os.getenv('MSAL_CLIENT_ID', ''),
            'client_secret': os.getenv('MSAL_CLIENT_SECRET', ''),
            'tenant_id': os.getenv('MSAL_TENANT_ID', ''),
            'sender': os.getenv('EMAIL_SENDER', ''),
            'recipients': recipients_list,
        }

