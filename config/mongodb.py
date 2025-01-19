from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from .settings import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME

def init_mongodb_connection():
    """
    Initialize MongoDB connection and return database and collection objects.
    
    Returns:
        tuple: (database, collection) MongoDB database and collection objects
    
    Raises:
        ValueError: If MONGO_URI is not set
        ConnectionFailure: If unable to connect to MongoDB
    """
    if not MONGO_URI:
        raise ValueError("MONGO_URI environment variable is not set!")

    try:
        # Create MongoDB client
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        
        # Get database and collection
        db = client[MONGO_DB_NAME]
        device_collection = db[MONGO_COLLECTION_NAME]
        
        return db, device_collection
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        raise ConnectionFailure(f"Failed to connect to MongoDB: {str(e)}")

def check_mongo_connection(db):
    """
    Check MongoDB connection status.
    
    Args:
        db: MongoDB database object
    
    Returns:
        str: 'connected' or 'disconnected'
    """
    try:
        db.command('ping')
        return 'connected'
    except (ConnectionFailure, ServerSelectionTimeoutError):
        return 'disconnected'

def get_device_collection():
    """
    Get device collection from MongoDB.
    
    Returns:
        Collection: MongoDB collection object for devices
    """
    _, collection = init_mongodb_connection()
    return collection