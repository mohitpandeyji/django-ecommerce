from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


class MailSender:
    @staticmethod
    def _send_email(subject, body, recipient_list):
        return send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=body
        )

    # ======================================== EMAIL ACTION UPDATES ===================

    def activate_user(self, recipient_list, token):
        context = dict(
            url=f"{settings.ASSETS_HOST}/user-registration/{token}",
        )
        html_content = render_to_string(template_name='emails/users/activate-user.html', context=context)
        self._send_email(

            subject="🎉 Welcome to Ecommerce!",
            body=html_content,
            recipient_list=[recipient_list]
        )

    def forgot_password(self, recipient_list, password_reset_token: str):
        context = dict(
            url=f"{settings.ASSETS_HOST}/reset-password/{password_reset_token}/"
        )

        html_content = render_to_string(
            template_name="emails/users/forget-password.html", context=context
        )

        self._send_email(
            subject="🔒 Forgotten Password - Ecommerce",
            body=html_content,
            recipient_list=recipient_list,
        )
