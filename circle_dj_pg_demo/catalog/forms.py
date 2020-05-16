import datetime 
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

class RenewBookForm(forms.Form):
    """Form for a librarian to renew books."""

    renewal_date = forms.DateField(help_text="between now and 4 weeks (default 3).")

    def clean_renewal_date(self):
        data = self.cleaned_data['renewal_date']        
        # validate the entered date
        if data < datetime.date.today():
            raise ValidationError(_('Invalid date - renewal in past'))
        elif data > datetime.date.today() + datetime.timedelta(weeks=4):
            raise ValidationError(_('Invalid date - renewal more than 4 weeks ahead'))
        return data
