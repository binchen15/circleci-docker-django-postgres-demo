import datetime
from django.test import TestCase
from django.urls import reverse
from catalog.models import Author
from django.utils import timezone
from django.contrib.auth.models import User        
from django.contrib.auth.models import Permission 
from catalog.models import BookInstance, Book, Subject, Language

class AuthorListViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        #Create authors for pagination tests
        number_of_authors = 13
        for author_num in range(number_of_authors):
           Author.objects.create(first_name='Christian {0}'.format(author_num), 
                                 last_name = 'Surname {0}'.format(author_num) )
           
    def test_view_url_exists_at_desired_location(self): 
        resp = self.client.get('/catalog/authors/') 
        self.assertEqual(resp.status_code, 200)  
           
    def test_view_url_reverse(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)
        
    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'catalog/author_list.html')
        
    def test_pagination_is_ten(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'] == True)
        self.assertTrue( len(resp.context['author_list']) == 10)

    def test_lists_all_authors(self):
        #Get second page and confirm it has (exactly) the remaining 3 items
        resp = self.client.get(reverse('authors')+'?page=2')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'] == True)
        self.assertTrue( len(resp.context['author_list']) == 3)
        

class LoanedBookInstancesByUserListViewTest(TestCase):

    def setUp(self):
        #Create two users
        test_user1 = User.objects.create_user(username='testuser1', password='12345') 
        test_user1.save()
        test_user2 = User.objects.create_user(username='testuser2', password='12345') 
        test_user2.save()
        
        #Create a book
        test_author   = Author.objects.create(first_name='John', last_name='Smith')
        test_subject  = Subject.objects.create(name='Fantasy')
        test_language = Language.objects.create(name='English')
        test_book     = Book.objects.create(title='Book Title', summary = 'My book summary', 
                                isbn='ABCDEFG', author=test_author, language=test_language)
        # Create subjects as a post-step
        subjects_for_book = Subject.objects.all()
        test_book.subjects.set(subjects_for_book)
        test_book.save()

        #Create 30 BookInstance objects
        number_of_book_copies = 30
        for book_copy in range(number_of_book_copies):
            return_date= timezone.now() + datetime.timedelta(days=book_copy%5)
            if book_copy % 2:
                the_borrower=test_user1
            else:
                the_borrower=test_user2
            status='m'  # non-existing status
            BookInstance.objects.create(book=test_book,
                                        imprint='Unlikely Imprint, 2016', 
                                        due_back=return_date, 
                                        borrower=the_borrower, 
                                        status=status)
        
    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('my-borrowed'))
        self.assertRedirects(resp, '/accounts/login/?next=/catalog/mybooks/')

    def test_logged_in_uses_correct_template(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertTemplateUsed(resp, 'catalog/bookinstance_list_borrowed_user.html')

    def test_only_borrowed_books_in_list(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(str(resp.context['user']), 'testuser1')
         
        #Check that initially we don't have any books in list (none on loan)
        self.assertTrue('bookinstance_list' in resp.context)
        self.assertEqual( len(resp.context['bookinstance_list']),0)
        
        #Now change 10 books to be on loan 
        get_ten_books = BookInstance.objects.all()[:10]
        for copy in get_ten_books:
            copy.status='o'
            copy.save()
        
        #Check that now we have borrowed books in the list
        resp = self.client.get(reverse('my-borrowed'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(str(resp.context['user']), 'testuser1')
        
        self.assertTrue('bookinstance_list' in resp.context) 
        #Confirm all books belong to testuser1 and are on loan
        for bookitem in resp.context['bookinstance_list']:
            self.assertEqual(resp.context['user'], bookitem.borrower)
            self.assertEqual('o', bookitem.status)

    def test_pages_paginated_to_ten(self):
    
        #Change all books to be on loan.
        #This should make 15 borrowed by testuser1.
        for copy in BookInstance.objects.all():
            copy.status='o'
            copy.save()
            
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))
        
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(str(resp.context['user']), 'testuser1')
                
        #Confirm that only 10 items are displayed due to pagination 
        # (if pagination not enabled, there would be 15 returned)
        self.assertEqual( len(resp.context['bookinstance_list']),10)

    def test_pages_ordered_by_due_date(self):
    
        #Change all books to be on loan
        for copy in BookInstance.objects.all():
            copy.status='o'
            copy.save()
            
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))
        
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(str(resp.context['user']), 'testuser1')
                
        #Confirm that of the items, only 10 are displayed due to pagination.
        self.assertEqual( len(resp.context['bookinstance_list']),10)
        
        last_date=0
        for copy in resp.context['bookinstance_list']:
            if last_date==0:
                last_date=copy.due_back
            else:
                self.assertTrue(last_date <= copy.due_back)
                

class RenewBookInstancesViewTest(TestCase):

    def setUp(self):
        #Create a user
        test_user1 = User.objects.create_user(username='testuser1', password='12345') 
        test_user1.save()
    
        test_user2 = User.objects.create_user(username='testuser2', password='12345') 
        test_user2.save()    
        permission = Permission.objects.get(name='Set book as returned')
        test_user2.user_permissions.add(permission)
        test_user2.save()
        
        #Create a book
        test_author   = Author.objects.create(first_name='John', last_name='Smith')
        test_subject  = Subject.objects.create(name='Fantasy')
        test_language = Language.objects.create(name='English')
        test_book     = Book.objects.create(title='Book Title', summary = 'My book summary', 
                           isbn='ABCDEFG', author=test_author, language=test_language)
        # Create genre as a post-step
        subjects_for_book = Subject.objects.all()
        test_book.subjects.set(subjects_for_book)
        test_book.save()

        #Create a BookInstance object for test_user1
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance1 = BookInstance.objects.create(
                    book=test_book,
                    imprint='Unlikely Imprint, 2016', 
                    due_back=return_date, 
                    borrower=test_user1, status='o')
        
        #Create a BookInstance object for test_user2
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance2 = BookInstance.objects.create(
                    book=test_book,imprint='Unlikely Imprint, 2016', 
                    due_back=return_date, 
                    borrower=test_user2, status='o')
        
    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('renew-book-librarian', 
								kwargs={'pk':self.test_bookinstance1.pk,}) )
        #Manually check redirect (Can't use assertRedirect, because the redirect URL is unpredictable)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/') )
        
    def test_redirect_if_logged_in_but_not_correct_permission(self):
        login = self.client.login(username='testuser1', password='12345')
        resp  = self.client.get(reverse('renew-book-librarian', kwargs={'pk':self.test_bookinstance1.pk,}) )
        
        #Manually check redirect (Can't use assertRedirect, because the redirect URL is unpredictable)
        self.assertEqual(resp.status_code,302)
        self.assertTrue(resp.url.startswith('/accounts/login/') )

    def test_logged_in_with_permission_borrowed_book(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk':self.test_bookinstance2.pk,}) )
        self.assertEqual( resp.status_code,200)

    def test_logged_in_with_permission_another_users_borrowed_book(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk':self.test_bookinstance1.pk,}) )
        self.assertEqual( resp.status_code,200)
        
    def test_uses_correct_template(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk':self.test_bookinstance1.pk,}) )
        self.assertEqual(resp.status_code,200)
        self.assertTemplateUsed(resp, 'catalog/book_renew_librarian.html')
        
    def test_form_renewal_date_initially_has_date_three_weeks_in_future(self):
        login = self.client.login(username='testuser2', password='12345')
        resp  = self.client.get(reverse('renew-book-librarian', kwargs={'pk':self.test_bookinstance1.pk,}) )
        self.assertEqual(resp.status_code,200)
        
        date_3_weeks_in_future = datetime.date.today() + datetime.timedelta(weeks=3)
        self.assertEqual(resp.context['form'].initial['renewal_date'], date_3_weeks_in_future )
        
    def test_form_invalid_renewal_date_past(self):
        login = self.client.login(username='testuser2', password='12345')
        
        date_in_past = datetime.date.today() - datetime.timedelta(weeks=1)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={'pk':self.test_bookinstance1.pk,}), 
                                {'renewal_date':date_in_past} )
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'renewal_date', 'Invalid date - renewal in past')
        
    def test_form_invalid_renewal_date_future(self):
        login = self.client.login(username='testuser2', password='12345')
        
        invalid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=5)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={'pk':self.test_bookinstance1.pk,}), 
								{'renewal_date':invalid_date_in_future} )
        self.assertEqual(resp.status_code,200)
        self.assertFormError(resp, 'form', 'renewal_date', 'Invalid date - renewal more than 4 weeks ahead')
        
    def test_redirects_to_all_borrowed_book_list_on_success(self):
        login = self.client.login(username='testuser2', password='12345')
        valid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=2)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={'pk':self.test_bookinstance1.pk,}), 
								{'renewal_date':valid_date_in_future} )
        self.assertRedirects(resp, reverse('all-borrowed'))

    def test_HTTP404_for_invalid_book_if_logged_in(self):
        import uuid 
        test_uid = uuid.uuid4() #unlikely UID to match our bookinstance!
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian', kwargs={'pk':test_uid,}) )
        self.assertEqual(resp.status_code, 404)
        

class AuthorCreateViewTest(TestCase):
    """Test case for the AuthorCreate view"""

    def setUp(self):
        #Create a user
        test_user1 = User.objects.create_user(username='testuser1', password='12345') 
        test_user1.save()
        
        test_user2 = User.objects.create_user(username='testuser2', password='12345') 
        test_user2.save()    
        permission = Permission.objects.get(name='Set book as returned')
        test_user2.user_permissions.add(permission)
        test_user2.save()
        
        #Create an author
        test_author = Author.objects.create(first_name='John', last_name='Smith')
 
    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('author_create') )
        self.assertRedirects(resp, '/accounts/login/?next=/catalog/author/create/' )
        
    def test_forbidden_if_logged_in_but_not_correct_permission(self):
        login = self.client.login(username='testuser1', password='12345')
        resp  = self.client.get(reverse('author_create'))
        self.assertEqual(resp.status_code, 403)
        
    def test_logged_in_with_permission(self):
        login = self.client.login(username='testuser2', password='12345')
        resp  = self.client.get(reverse('author_create') )
        self.assertEqual(resp.status_code, 200)
        
    def test_uses_correct_template(self):
        login = self.client.login(username='testuser2', password='12345')
        resp  = self.client.get(reverse('author_create') )
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'catalog/author_form.html')
         
    def test_form_date_of_death_initially_set_to_expected_date(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('author_create') )
        self.assertEqual(resp.status_code, 200)

        expected_initial_date = datetime.date(2018, 1, 5)
        response_date=resp.context['form'].initial['date_of_death']
        response_date=datetime.datetime.strptime(response_date, "%d/%m/%Y").date()
        self.assertEqual(response_date, expected_initial_date)
        
    def test_redirects_to_detail_view_on_success(self):
        login = self.client.login(username='testuser2', password='12345')
        resp  = self.client.post(reverse('author_create'),
								{'first_name':'Christian Name','last_name':'Surname',} )
        #Manually check redirect because we don't know what author was created
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/catalog/author/') )
