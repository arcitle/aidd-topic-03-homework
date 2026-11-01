from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from user.models import User


class RegistrationForm(forms.Form):
    """Форма регистрации пользователей"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Email"}
        ),
    )
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Пароль"}
        ),
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Повторите пароль"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data:
            return cleaned_data

        email = cleaned_data.get("email", "").strip().lower()
        cleaned_data["email"] = email
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            errors = ["Введенные пароли не совпадают"]
            raise ValidationError(errors)

        if not email:
            return cleaned_data
        user = User.objects.filter(email__iexact=email)

        if user:
            errors = [
                "Данный e-mail уже зарегистрирован! Введите другой e-mail или"
                " воспользуйтесь формой авторизации."
            ]
            raise ValidationError(errors)

        return cleaned_data

    def save(self):
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        user = User.objects.create_user(email, email, password)
        return authenticate(username=email, password=password) or user


class AuthForm(forms.Form):
    """Форма авторизации пользователей"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Email"}
        ),
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Пароль"}
        ),
    )
