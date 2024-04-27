from django import forms
from stripe import Review 
from core.models import ProductReview


class ProductReviewForm(forms.ModelForm):
    review = forms.CharField(widget=forms.Textarea(attrs={'placeholder': "Write review"}))

    class Meta:
        model = ProductReview
        fields = ['review', 'rating']


from userauths.models import ContactUs
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactUs
        fields = ['full_name', 'email', 'phone', 'subject', 'message']