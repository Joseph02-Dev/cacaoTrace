from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Village

GENERIC_LOGIN_ERROR = {"detail": "Identifiant ou mot de passe incorrect."}


def _decimal_or_none(value):
    return str(value) if value is not None else None


def _serialize_bootstrap(user: User) -> dict:
    villages = (
        Village.objects.filter(company_id=user.company_id, status=Village.STATUS_ACTIVE)
        .order_by("name")
    )
    return {
        "user": {
            "id": str(user.id),
            "code": user.code,
            "name": user.name,
            "role": user.role,
            "company_id": str(user.company_id),
        },
        "company": {
            "id": str(user.company_id),
            "name": user.company.name,
            "standard_bag_weight_kg": str(user.company.standard_bag_weight_kg),
        },
        "villages": [
            {
                "id": str(v.id),
                "name": v.name,
                "prefecture": v.prefecture,
                "latitude": _decimal_or_none(v.latitude),
                "longitude": _decimal_or_none(v.longitude),
            }
            for v in villages
        ],
    }


class LoginView(APIView):
    """POST /api/auth/login — contrat figé dans dev-cacaotrack-gn.md (API-1 + API-4)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        identifier = (request.data.get("identifier") or "").strip().lower()
        password = request.data.get("password") or ""

        if not identifier or not password:
            return Response(
                {"detail": "Identifiant et mot de passe requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.select_related("company").get(code=identifier)
        except User.DoesNotExist:
            return Response(GENERIC_LOGIN_ERROR, status=status.HTTP_401_UNAUTHORIZED)

        if user.is_locked():
            return Response(
                {"detail": "Compte temporairement verrouillé. Réessayez plus tard."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not user.is_active or not user.check_password(password):
            if user.is_active:
                user.register_failed_attempt()
            return Response(GENERIC_LOGIN_ERROR, status=status.HTTP_401_UNAUTHORIZED)

        user.reset_failed_attempts()

        refresh = RefreshToken.for_user(user)
        payload = {"access": str(refresh.access_token), "refresh": str(refresh)}
        payload.update(_serialize_bootstrap(user))
        return Response(payload, status=status.HTTP_200_OK)


class RefreshView(APIView):
    """POST /api/auth/refresh — refuse si l'utilisateur est désactivé (contrat dev)."""

    permission_classes = [AllowAny]

    def post(self, request):
        token_str = request.data.get("refresh")
        if not token_str:
            return Response(
                {"detail": "Jeton de renouvellement requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(token_str)
        except TokenError:
            return Response(
                {"detail": "Jeton invalide ou expiré."}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            user = User.objects.get(id=refresh.get("user_id"))
        except (User.DoesNotExist, ValueError):
            return Response({"detail": "Jeton invalide."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail": "Utilisateur désactivé."}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({"access": str(refresh.access_token)}, status=status.HTTP_200_OK)
