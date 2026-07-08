from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken

def create_user_tokens(user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    # Access token muddati (SIMPLE_JWT.ACCESS_TOKEN_LIFETIME bilan mos)
    access.set_exp(lifetime=timedelta(minutes=30))

    return str(access), str(refresh), int(timedelta(minutes=30).total_seconds())