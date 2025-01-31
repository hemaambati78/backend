#Install Dependencies 
pip install django djangorestframework django-ckeditor django-redis googletrans==4.0.0-rc1
#Create Django Project and App
django-admin startproject faq_project
cd faq_project
python manage.py startapp faq_app
#Add Apps to INSTALLED_APPS
 #Update faq_project/settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'ckeditor',
    'faq_app',
]
#Configure Redis Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
#FAQ Model
from django.db import models
from django.utils.translation import gettext_lazy as _
from ckeditor.fields import RichTextField
from googletrans import Translator

class FAQ(models.Model):
    question = models.TextField(_("Question"))
    answer = RichTextField(_("Answer"))  # WYSIWYG editor support
    question_hi = models.TextField(_("Question (Hindi)"), blank=True, null=True)
    answer_hi = models.TextField(_("Answer (Hindi)"), blank=True, null=True)
    question_bn = models.TextField(_("Question (Bengali)"), blank=True, null=True)
    answer_bn = models.TextField(_("Answer (Bengali)"), blank=True, null=True)

    def get_translated_question(self, lang):
        """Retrieve translated question dynamically."""
        cache_key = f"faq_{self.id}_question_{lang}"
        cached_value = cache.get(cache_key)
        if cached_value:
            return cached_value
        translated = getattr(self, f"question_{lang}", self.question)
        cache.set(cache_key, translated, timeout=60*60)  # Cache for 1 hour
        return translated

    def get_translated_answer(self, lang):
        """Retrieve translated answer dynamically."""
        cache_key = f"faq_{self.id}_answer_{lang}"
        cached_value = cache.get(cache_key)
        if cached_value:
            return cached_value
        translated = getattr(self, f"answer_{lang}", self.answer)
        cache.set(cache_key, translated, timeout=60*60)  # Cache for 1 hour
        return translated

    def save(self, *args, **kwargs):
        """Automate translations during object creation."""
        translator = Translator()
        if not self.question_hi:
            self.question_hi = translator.translate(self.question, dest='hi').text
        if not self.answer_hi:
            self.answer_hi = translator.translate(self.answer, dest='hi').text
        if not self.question_bn:
            self.question_bn = translator.translate(self.question, dest='bn').text
        if not self.answer_bn:
            self.answer_bn = translator.translate(self.answer, dest='bn').text
        super().save(*args, **kwargs)

    def __str__(self):
        return self.question
    #Serializer and ViewSet
from rest_framework import serializers
from .models import FAQ

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer']
from rest_framework import viewsets
from .models import FAQ
from .serializers import FAQSerializer

class FAQViewSet(viewsets.ModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer

    def get_queryset(self):
        lang = self.request.query_params.get('lang', 'en')
        queryset = super().get_queryset()
        for faq in queryset:
            faq.question = faq.get_translated_question(lang)
            faq.answer = faq.get_translated_answer(lang)
        return queryset      
    # Register API URLs
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from faq_app.views import FAQViewSet

router = DefaultRouter()
router.register(r'faqs', FAQViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
# Admin Panel Configuration
from django.contrib import admin
from .models import FAQ

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'answer')
#python manage.py makemigrations
#python manage.py migrate
python manage.py createsuperuser

from django.test import TestCase
from .models import FAQ

class FAQTests(TestCase):
    def test_faq_translation(self):
        faq = FAQ.objects.create(question="What is Django?", answer="Django is a web framework.")
        self.assertEqual(faq.get_translated_question('hi'), faq.question_hi)

#Create Dockerfile:
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    depends_on:
      - redis
  redis:
    image: redis:latest