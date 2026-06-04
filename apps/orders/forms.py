from django import forms
from django.core.validators import RegexValidator


class OrderForm(forms.Form):
    first_name = forms.CharField(
        label="Имя", max_length=100,
        widget=forms.TextInput(attrs={"autocomplete": "given-name", "placeholder": "Иван"})
    )
    last_name = forms.CharField(
        label="Фамилия", max_length=100,
        widget=forms.TextInput(attrs={"autocomplete": "family-name", "placeholder": "Иванов"})
    )
    patronymic = forms.CharField(
        label="Отчество", max_length=100, required=False,
        widget=forms.TextInput(attrs={"placeholder": "Иванович (необязательно)"})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "ivan@example.com"})
    )
    phone = forms.CharField(
        label="Телефон", max_length=20, required=False,
        validators=[RegexValidator(r"^\+?[\d\s\-\(\)]{7,20}$", "Некорректный номер телефона")],
        widget=forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "+7 999 000-00-00"})
    )
    promo_code = forms.CharField(label="Промокод", max_length=50, required=False)
    consent = forms.BooleanField(
        label=(
            "Я соглашаюсь с <a href='/documents/offer/' target='_blank'>офертой</a> "
            "и даю согласие на <a href='/documents/privacy/' target='_blank'>"
            "обработку персональных данных</a>"
        ),
        error_messages={"required": "Необходимо принять условия"},
    )

    def __init__(self, *args, ticket_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ticket_type = ticket_type

    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()

    def clean_first_name(self):
        v = self.cleaned_data["first_name"].strip()
        if any(c.isdigit() for c in v):
            raise forms.ValidationError("Имя не должно содержать цифры")
        return v

    def clean_last_name(self):
        v = self.cleaned_data["last_name"].strip()
        if any(c.isdigit() for c in v):
            raise forms.ValidationError("Фамилия не должна содержать цифры")
        return v
