import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists, helpful for local testing
load_dotenv()

class Config:
    """
    Configuration settings for Flask Application.
    Credentials can be overridden via environment variables for AWS EC2/RDS deployment.
    """
    # Application Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-key-student-management-system-98213')

    # MySQL / Amazon RDS Settings
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'student_db')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    # Connection Pool Settings
    MYSQL_POOL_SIZE = int(os.environ.get('MYSQL_POOL_SIZE', 5))
    MYSQL_POOL_NAME = "student_mgr_pool"

    # SMTP Mail Server Settings (For OTP checks and fee layout communications)
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_SENDER = os.environ.get('SMTP_SENDER', 'no-reply@edumanager.edu')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() in ('1', 'true', 'yes', 'on')
