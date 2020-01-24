from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from emails.mail_sender import MailSender
from ecommerce.decorators import access_permissions
from ecommerce.utilities.view_mixins import GenericBaseView
from users.models import User, PasswordResetToken
from users.serializers import MyTokenObtainPairSerializer, UserSerializer, \
    ActivateUserDeserializer, CreateBasicUserDeserializer, UserDeserializer, BaseUserSerializer, \
    WebResetPasswordDeserializer, ChangePasswordDeserializer


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class CurrentUsersDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request):
        user = request.user
        data = UserSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        serializer = UserDeserializer(instance=user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class CreateBasicUserView(APIView):
    """
    Create basic user
    """

    @access_permissions('users.add_user')
    def post(self, request):
        deserializer = CreateBasicUserDeserializer(data=request.data)
        deserializer.is_valid(raise_exception=True)
        user = deserializer.save()
        data = UserSerializer(user).data

        # TODO : Later Make it as task
        MailSender().activate_user(recipient_list=data['email'], token=user.uuid)

        return Response(data, status=status.HTTP_201_CREATED)


class ActivateUserView(APIView):
    """
    Complete user registration from received email
    """
    permission_classes = (AllowAny,)

    def get(self, _request):
        uuid = self.request.query_params.get('token')
        if not uuid:
            return Response({'token': 'token is required'}, status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, uuid=uuid)
        if user.activation_status == User.STATUS_ACCEPTED:
            return Response({'error': 'Invalid Link'}, status=status.HTTP_226_IM_USED)
        return Response(BaseUserSerializer(user).data, status=status.HTTP_200_OK)

    def patch(self, request):
        if not request.data.get('token'):
            return Response({'token': 'token is required'}, status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, uuid=request.data['token'])
        if user.activation_status == User.STATUS_ACCEPTED:
            return Response({'error': 'Invalid Link'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ActivateUserDeserializer(instance=user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        serializer = UserSerializer(user)
        return Response(serializer.data)


class UsersDetailView(APIView):

    @access_permissions('users.view_user')
    def get(self, _request: Request):
        user_id = self.request.query_params.get('user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            data = UserSerializer(user)
            return Response(data.data, status=status.HTTP_200_OK)
        user = User.objects.all().exclude(username="AnonymousUser").order_by('-created_at')
        data = UserSerializer(user, many=True)
        return Response(data.data, status=status.HTTP_200_OK)

    @access_permissions('users.change_user')
    def patch(self, request):
        user_id = self.request.query_params.get('user_id')
        user = get_object_or_404(User.objects.all(), pk=user_id)
        serializer = UserDeserializer(instance=user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = UserSerializer(user).data
        return Response(data)

    @access_permissions('users.delete_user')
    def delete(self, _request):
        user_id = self.request.query_params.get('user_id')
        user = get_object_or_404(User.objects.all(), pk=user_id)
        user.is_active = False
        user.save()
        return Response({"message": "user with id `{}` has been inactivated."
                        .format(user_id)}, status=204)


class RequestResetPasswordView(GenericBaseView):
    """
    Request a password reset for the user.
    """

    requires_authentication = False

    def post(self, request, **_kwargs):
        email = request.data.get("email", None)
        if email is None:
            return Response(
                {"email": [_("This field is required")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'status': 'Failed',
                'code': status.HTTP_404_NOT_FOUND,
                'message': 'Email not found.',
                'data': []
            }, status=status.HTTP_404_NOT_FOUND)

        PasswordResetToken.objects.filter(user=user).delete()
        token = PasswordResetToken.objects.create(user=user)
        # user = token.user

        # TODO : Later Make it as celery task
        MailSender().forgot_password(recipient_list=[user.email], password_reset_token=token.token)

        return Response({
            'status': 'Success',
            'code': status.HTTP_200_OK,
            'message': 'Email sent to your mail',
            'data': []
        }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """
    Reset a password for the user for forget password mail
    """
    requires_authentication = False

    def post(self, request, **_kwargs):
        deserializer = WebResetPasswordDeserializer(data=request.data)
        deserializer.is_valid(raise_exception=True)
        deserializer.save()
        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Password updated successfully',
            'data': []
        }

        return Response(response, status=status.HTTP_200_OK)


class ChangePasswordView(UpdateAPIView):
    """
    Change a password for the user.
    """
    """
        An endpoint for changing password.
        """
    permission_classes = (IsAuthenticated,)

    def get_object(self, queryset=None):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = ChangePasswordDeserializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            old_password = serializer.data.get("old_password")
            if not self.object.check_password(old_password):
                return Response({"old_password": ["Your current password doesn't matched"]},
                                status=status.HTTP_400_BAD_REQUEST)
            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Password updated successfully',
                'data': []
            }

            return Response(response, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
