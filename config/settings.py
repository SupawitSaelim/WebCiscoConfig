import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask Configuration
SECRET_KEY = 'Supawitadmin123_'
DEBUG = True
PORT = 5000
HOST = "0.0.0.0"

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = 'device_management'
MONGO_COLLECTION_NAME = 'devices'

# SSH Manager Configuration
MAX_SSH_SESSIONS = 50
SSH_SESSION_TIMEOUT = 3600  # 1 hour in seconds

# Security Configuration
MODEL_PATH = 'models/ml/lr_model.pkl'
TIMEZONE = 'Asia/Bangkok'

# Scheduler Configuration
SECURITY_CHECK_INTERVAL = 10  # seconds
SSH_CLEANUP_INTERVAL = 300    # 5 minutes
LONG_RUNNING_CLEANUP_INTERVAL = 3600  # 1 hour

# Define all configuration classes
class Config:
    """Base configuration."""
    SECRET_KEY = SECRET_KEY
    DEBUG = DEBUG
    MONGO_URI = MONGO_URI
    TIMEZONE = TIMEZONE
    HOST = HOST
    PORT = PORT

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True

# Create config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Set active configuration
active_config = config[os.getenv('FLASK_ENV', 'development')]