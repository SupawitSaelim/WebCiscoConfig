from flask import Blueprint, request, jsonify

def init_device_search_routes(device_collection):
    """Initialize device search routes blueprint"""
    bp = Blueprint('device_search', __name__)
    
    @bp.route('/search_hostname', methods=['GET'])
    def search_hostname():
        """
        Search for device hostnames matching the query
        Used for autocomplete/suggestion in hostname input fields
        """
        query = request.args.get('query', '')
        if query:
            matching_devices = device_collection.find(
                {"name": {"$regex": query, "$options": "i"}}
            )
            device_names = [device["name"] for device in matching_devices]
            return jsonify(device_names)
        return jsonify([])
            
    return bp