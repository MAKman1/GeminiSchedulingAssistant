from functools import wraps
from flask import request, jsonify, g
import firebase_admin
from firebase_admin import auth

def token_required(f):
    """
    A decorator to ensure a valid Firebase ID token is present in the request.
    The decoded user information is attached to Flask's `g.current_user`.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers and request.headers['Authorization'].startswith('Bearer '):
            token = request.headers['Authorization'].split('Bearer ')[1]

        if not token:
            return jsonify({"error": "Authentication token is missing or invalid."}), 401

        try:
            # Verify the ID token using the Firebase Admin SDK.
            # This verifies the signature and expiration of the token.
            decoded_token = auth.verify_id_token(token)
            # Attach the decoded token to Flask's global context object `g`.
            # This makes the user's info (like UID, email) available in the route.
            g.current_user = decoded_token
        except auth.InvalidIdTokenError:
            return jsonify({"error": "Invalid authentication token."}), 401
        except Exception as e:
            print(f"Error during token verification: {e}")
            return jsonify({"error": "An unexpected error occurred during authentication."}), 500

        return f(*args, **kwargs)
    return decorated_function
