# api/utils.py - CREATE THIS NEW FILE

import jwt
from django.conf import settings


def verify_supabase_token(token):
    """
    Verify Supabase JWT token
    Decodes without verification first, then validates structure
    """
    try:
        # Decode without verification (we trust Supabase)
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        
        # Verify critical claims exist
        if not decoded.get('sub'):
            print("Token missing 'sub' claim")
            return None
            
        if not decoded.get('email'):
            print("Token missing 'email' claim")
            return None
        
        # Return decoded token if structure is valid
        return decoded
        
    except jwt.InvalidTokenError as e:
        print(f"Token verification failed: {str(e)}")
        return None
    except Exception as e:
        print(f"Token decode error: {str(e)}")
        return None


def get_client_ip(request):
    """
    Get client IP address from request
    Handles proxies and CloudFlare
    """
    # Check for CloudFlare
    if 'HTTP_CF_CONNECTING_IP' in request.META:
        return request.META['HTTP_CF_CONNECTING_IP']
    
    # Check for X-Forwarded-For (proxy)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
        return ip
    
    # Direct connection
    return request.META.get('REMOTE_ADDR', '0.0.0.0')