from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken

def create_user_tokens(user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    # 🔥 LOGIN dagidek 13 soat
    access.set_exp(lifetime=timedelta(hours=13))

    return str(access), str(refresh), int(timedelta(hours=13).total_seconds())