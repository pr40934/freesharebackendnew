from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, UserSession


# ============================================
# AUTH SERIALIZERS (NEW)
# ============================================

class UserProfileSerializer(serializers.ModelSerializer):
    """Serialize user profile data"""
    email = serializers.CharField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'supabase_user_id',
            'username',
            'email',
            'full_name',
            'avatar_url',
            'phone',
            'bio',
            'is_email_verified',
            'last_login_ip',
            'last_login_date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'supabase_user_id',
            'last_login_ip',
            'last_login_date',
            'created_at',
            'updated_at',
        ]


class UserSessionSerializer(serializers.ModelSerializer):
    """Serialize user session data"""
    device_info = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            'id',
            'ip_address',
            'user_agent',
            'device_info',
            'is_active',
            'created_at',
            'last_activity',
            'expires_at',
        ]
        read_only_fields = [
            'ip_address',
            'user_agent',
            'created_at',
            'last_activity',
            'expires_at',
        ]

    def get_device_info(self, obj):
        """Extract device info from user agent"""
        user_agent = obj.user_agent.lower()
        
        # Detect OS
        if 'windows' in user_agent:
            os_name = 'Windows'
        elif 'mac' in user_agent:
            os_name = 'macOS'
        elif 'linux' in user_agent:
            os_name = 'Linux'
        elif 'iphone' in user_agent:
            os_name = 'iOS'
        elif 'android' in user_agent:
            os_name = 'Android'
        else:
            os_name = 'Unknown'

        # Detect browser
        if 'chrome' in user_agent:
            browser = 'Chrome'
        elif 'firefox' in user_agent:
            browser = 'Firefox'
        elif 'safari' in user_agent:
            browser = 'Safari'
        elif 'edge' in user_agent:
            browser = 'Edge'
        else:
            browser = 'Unknown'

        return {
            'os': os_name,
            'browser': browser,
        }


# ============================================
# YOUR EXISTING SERIALIZERS - KEEP THEM BELOW
# ============================================
# Paste your existing serializers here
# They stay completely unchanged