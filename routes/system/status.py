from flask import Blueprint, jsonify

def init_system_status_routes(db):
    """Initialize system status routes blueprint"""
    bp = Blueprint('system_status', __name__)
    
    @bp.route('/mongo_status')
    def mongo_status():
        """Check MongoDB connection status"""
        try:
            db.command('ping')
            return jsonify({"status": "connected"})
        except Exception:
            return jsonify({"status": "disconnected"})
            
    return bp