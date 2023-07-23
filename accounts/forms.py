from django import forms
from .models import Account ,UserProfile

# ##Form logic to capture registration information

class RegisterForms(forms.ModelForm):
    # ##Field declarations
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        # 'placeholder' : 'Enter Password',
        'class' : 'form-control',
    }))
    repeat_password = forms.CharField(widget=forms.PasswordInput(attrs={
        # 'placeholder' : 'Repeat Password',
        'class' : 'form-control',
    }))
    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'Phone_number', 'email', 'password']

    def __init__(self, *args, **kwargs):
        super(RegisterForms, self).__init__(*args, **kwargs)
        # self.fields['first_name'].widget.attrs['placeholder'] = 'First name'
        # self.fields['last_name'].widget.attrs['placeholder'] = 'Last name'
        # self.fields['email'].widget.attrs['placeholder'] = 'Email'
        # self.fields['Phone_number'].widget.attrs['placeholder'] = 'Phone Number'
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'input100'

    
    def clean(self):
        cleaned_data = super(RegisterForms, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('repeat_password')

        if password != confirm_password:
            raise forms.ValidationError(
                "Password does not match!"
            )
        
      

class UserForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ('first_name', 'last_name', 'Phone_number')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

class UserProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(required=False, error_messages = {'invalid':("Image files only")}, widget=forms.FileInput)
    class Meta:
        model = UserProfile
        fields = ('address', 'city', 'state', 'country', 'profile_picture')

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
