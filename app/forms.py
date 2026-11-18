from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["trainer", "rating", "text"]
        labels = {"trainer": "Тренер", "rating": "Оценка (1-5)", "text": "Ваш отзыв"}

class FeedbackForm(forms.Form):
    name = forms.CharField(max_length=100, label="Ваше имя")
    phone = forms.CharField(max_length=20, label="Телефон")
    message = forms.CharField(widget=forms.Textarea, label="Сообщение")

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if len("".join(ch for ch in phone if ch.isdigit())) < 10:
            raise forms.ValidationError("Введите корректный номер телефона.")
        return phone

class FreezeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Начало")
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Конец")