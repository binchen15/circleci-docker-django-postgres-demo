import uuid 
from datetime import date
from django.db import models
from django.urls import reverse 
from django.contrib.auth.models import User #Required to assign User as a borrower

# Create your models here.

class Subject(models.Model):
    """Model representing a book subject"""
    name = models.CharField(max_length=255, help_text="Enter a book subject.")
    
    def __str__(self):
        return self.name
        
        
class Language(models.Model):
    """Model representing a Language (e.g. English)"""
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name
        
        
class Book(models.Model):
    """Model representing a book (but not a specific copy of a book). """
    title   = models.CharField(max_length=255)
    author  = models.ForeignKey('Author', 
                                on_delete=models.SET_NULL, null=True)
    summary = models.TextField(max_length=1000, 
                               help_text="Enter a brief description of the book")
    isbn    = models.CharField('ISBN', max_length=13, 
                               help_text='13 Character ISBN number')
    language = models.ForeignKey('Language', 
                                 on_delete=models.SET_NULL, null=True)
    subjects = models.ManyToManyField(Subject, 
                                 help_text="Select a subject for this book")
      
    def display_subject(self):
        return ', '.join([ sub.name for sub in self.subjects.all()[:3] ])
        display_subject.short_description = 'Subject'
    
    
    def get_absolute_url(self):
        return reverse('book-detail', args=[str(self.id)])

    def __str__(self):
        return self.title
        
        
class BookInstance(models.Model):
    """Model representing a specific copy of a book."""

    LOAN_STATUS = (
        ('d', 'Maintenance'),
        ('o', 'On loan'),
        ('a', 'Available'),
        ('r', 'Reserved'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, 
                          help_text="Unique ID for this book across library")
    book     = models.ForeignKey('Book', on_delete=models.SET_NULL, null=True) 
    imprint  = models.CharField(max_length=200)
    due_back = models.DateField(null=True, blank=True)
    borrower = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    status   = models.CharField(max_length=1, choices=LOAN_STATUS, blank=True, default='d', 
                                help_text='Book availability')
    
    @property
    def is_overdue(self):
        return self.due_back and date.today() > self.due_back
        
    class Meta:
        ordering = ["due_back"]
        permissions = (("can_mark_returned", "Set book as returned"),)   

    def __str__(self):
        return '{0} ({1})'.format(self.id,self.book.title)
        

class Author(models.Model):
    """Model representing an author."""

    first_name    = models.CharField(max_length=100)
    last_name     = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_death = models.DateField('died', null=True, blank=True)

    class Meta:
        ordering = ["last_name","first_name"]
    
    def get_absolute_url(self):
        return reverse('author-detail', args=[str(self.id)])
    
    def __str__(self):
        return '{0}, {1}'.format(self.last_name,self.first_name)


