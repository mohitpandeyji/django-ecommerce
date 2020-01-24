from django.urls import path
from rest_framework_simplejwt import views as jwt_views

from users.views import MyTokenObtainPairView, CurrentUsersDetailView, CreateBasicUserView, \
    UsersDetailView, ActivateUserView, RequestResetPasswordView, \
    ResetPasswordView, ChangePasswordView
app_name = 'users'
urlpatterns = [
    path('', UsersDetailView.as_view(), name='list_all_users_details'),
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', jwt_views.TokenVerifyView.as_view(), name='token_verify'),
    path('current/', CurrentUsersDetailView.as_view(), name='current_user_detail'),
    path('create-basic/', CreateBasicUserView.as_view(), name='create_basic_user'),
    path('activate/', ActivateUserView.as_view(), name='activate_user'),
    path("request-password-reset/", RequestResetPasswordView.as_view(), name="request_password_reset"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),

]
