import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class QuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=99)


class CheckoutForm(forms.Form):
    name = forms.CharField(label='Ваше имя', max_length=120)
    email = forms.EmailField(label='Email')
    phone = forms.CharField(label='Телефон', max_length=30, widget=forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel'}))
    comment = forms.CharField(label='Комментарий к заказу', required=False, max_length=1500, widget=forms.Textarea(attrs={'rows': 3, 'class': 'w-100'}))
    consent = forms.BooleanField(label='Согласен на обработку данных для оформления заказа', widget=forms.CheckboxInput(attrs={'style': 'width:18px;height:18px;flex-shrink:0'}))

    def clean_phone(self):
        value = self.cleaned_data['phone'].strip()
        if not 10 <= len(re.sub(r'\D', '', value)) <= 15:
            raise forms.ValidationError('Укажите телефон: от 10 до 15 цифр.')
        return value


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label='Email', required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
