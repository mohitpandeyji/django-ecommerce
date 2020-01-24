from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, email, username, password, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        if not username or not email:
            raise ValueError('Users must have username and email')

        user = self.model.objects.create(
            email=self.normalize_email(email),
            username=username,
            **extra_fields
        )

        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, username, password, **extra_fields):
        """
        Creates and saves a superuser with the given username, email and password.
        """
        user = self.create_user(
            email, username, password, **extra_fields
        )
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        return user
