"""URLs of the app accounts."""
from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import auth as auth_views
from .views import user as user_views

router = DefaultRouter()
router.register("admin-users", user_views.AdminUserViewSet,
                basename="admin-users")

urlpatterns = [
    # Auth views
    path(
        "validate/username/",
        auth_views.ValidateUsername.as_view(),
        name="validate-username",
    ),
    path(
        "validate/password/",
        auth_views.ValidatePassword.as_view(),
        name="validate-password",
    ),
    path("validator/", auth_views.ManageValidator.as_view(), name="validator"),
    path(
        "password/forgot/",
        auth_views.ResetPassword.as_view(),
        name="forgot-password",
    ),
    path(
        "password/set/", auth_views.SetPassword.as_view(), name="set-password"
    ),
    path("device/", auth_views.CreateUserDevice.as_view(), name="user-device"),
    path("signup/", auth_views.Signup.as_view(), name="signup"),
    path("login/", auth_views.Login.as_view(), name="login"),
    path(
        "login/google/", auth_views.GoogleLogin.as_view(), name="google-login"
    ),
    path("login/magic/", auth_views.MagicLogin.as_view(), name="magic-login"),
    path(
        "login/email-login/",
        auth_views.EmailLogin.as_view(),
        name="email-login",
    ),
    path(
        "login/code-verify/",
        auth_views.EmailLoginCode.as_view(),
        name="code-verify",
    ),
    path(
        "magic/generate/",
        auth_views.MagicLink.as_view(),
        name="magic-generate",
    ),
    path("logout/", auth_views.Logout.as_view(), name="logout"),
    path(
        "verify-email/resend/",
        auth_views.VerificationEmail.as_view(),
        name="resend-email",
    ),
    path(
        "invitee-user/",
        auth_views.InviteeUserViewSet.as_view({"get": "list"}),
        name="invitee-user",
    ),
    path(
        "invitee-user/<idencode:pk>/",
        auth_views.InviteeUserViewSet.as_view(
            {"put": "update", "patch": "partial_update"}
        ),
        name="invitee-user",
    ),
    # For password confirmation inside the system, without logging out user
    path("check/password/", auth_views.CheckPassword.as_view()),
    # User Views
    path("user/search/", user_views.UserList.as_view(), name="user-search"),
    path(
        "user/<idencode:pk>/",
        user_views.UserDetails.as_view(),
        name="user-details",
    ),
    path("user/", user_views.UserDetails.as_view(), name="user-view"),
    path("terms/", user_views.TermsAndConditionsDetails.as_view(),
         name="terms"),
    # Admin Login
    path(
        "admin/login/",
        auth_views.FFAdminLogin.as_view(),
        name="ff-admin-login",
    ),
    # Admin Dashboard V3
    path("admin/", include(router.urls)),
]
