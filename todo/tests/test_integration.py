from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from todo.models import Todo

class TodoIntegrationTests(TestCase):

    def test_signup_login_redirect(self):
        """Проверка на регистрацию, логин и редирект к задачам"""

        signup_data = {
            'username': 'hello_user',
            'password1': 'my_password',
            'password2': 'my_password',
        }

        resp = self.client.post(reverse('user_signup'), signup_data)

        self.assertEqual(resp.status_code, 302)

        self.assertTrue(User.objects.filter(username='hello_user').exists())

        login_data = {'username': 'hello_user', 'password': 'my_password'}
        resp2 = self.client.post(reverse('user_login'), login_data)
        self.assertEqual(resp2.status_code, 302)

        user = resp2.wsgi_request.user
        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.username, 'hello_user')

    def test_create_check_tasks(self):
        """Создание задачи и проверка ее появления"""

        u = User.objects.create_user(username='bob', password='pwd')
        self.client.force_login(u)

        data = {
            'title': 'Buy milk',
            'memo': 'From supermarket',
        }

        resp = self.client.post(reverse('createtodo'), data=data)
        self.assertEqual(resp.status_code, 302)

        todos = Todo.objects.filter(user=u)
        self.assertEqual(todos.count(), 1)
        todo = todos.first()

        self.assertEqual(todo.title, 'Buy milk')
        self.assertEqual(todo.memo, 'From supermarket')

        resp_list = self.client.get(reverse('currenttodos'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'Buy milk')
    
    def test_create_check_multiple_tasks(self):
        """Проверка нескольких задач"""

        u = User.objects.create_user(username='Tom', password='my_pwd')
        self.client.force_login(u)

        data1 = {
            'title': 'Buy meet',
            'memo': 'Delicious!',
        }

        data2 = {
            'title': 'Play football',
            'memo': 'Cool!',
        }

        resp = self.client.post(reverse('createtodo'), data=data1)
        self.assertEqual(resp.status_code, 302)

        resp = self.client.post(reverse('createtodo'), data=data2)
        self.assertEqual(resp.status_code, 302)

        todos = Todo.objects.filter(user=u)
        self.assertEqual(todos.count(), 2)
        todo1 = todos.first()
        todo2 = todos.last()

        self.assertEqual(todo1.title, 'Buy meet')
        self.assertEqual(todo1.memo, 'Delicious!')

        self.assertEqual(todo2.title, 'Play football')
        self.assertEqual(todo2.memo, 'Cool!')

        resp_list = self.client.get(reverse('currenttodos'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'Buy meet')
        self.assertContains(resp_list, 'Delicious!')
        self.assertContains(resp_list, 'Play football')
        self.assertContains(resp_list, 'Cool!')

    def test_view_others_tasks(self):
        """Проверка на недоступность задачи другого пользователя"""

        owner = User.objects.create_user(username='owner', password='first')
        other = User.objects.create_user(username='other', password='second')
        t = Todo.objects.create(user=owner, title='Secret task', memo='top secret')

        self.client.force_login(other)
        resp = self.client.get(reverse('viewtodo', kwargs={'todo_pk': t.pk}))

        self.assertEqual(resp.status_code, 404)

    def test_edit_task(self):
        """Проверка на исправное редактирование задачи"""

        u = User.objects.create_user(username='John', password='p')
        self.client.force_login(u)

        t = Todo.objects.create(user=u, title='Old title', memo='Old memo')

        data_edit = {
            'title': 'New title',
            'memo': 'New memo',
        }

        resp = self.client.post(reverse('viewtodo', kwargs={'todo_pk': t.pk}), data=data_edit)
        self.assertEqual(resp.status_code, 302)

        t.refresh_from_db()

        self.assertEqual(t.title, 'New title')
        self.assertEqual(t.memo, 'New memo')

    def test_complete_task(self):
        """Проверка на корректное поведение при завершении задачи"""

        u = User.objects.create_user(username='Dave', password='p')
        self.client.force_login(u)

        t = Todo.objects.create(user=u, title='To finish', memo='...')

        resp = self.client.post(reverse('completetodo', kwargs={'todo_pk': t.pk}))
        self.assertEqual(resp.status_code, 302)

        t.refresh_from_db()
        self.assertIsNotNone(t.completed)

        resp_completed = self.client.get(reverse('completedtodos'))
        self.assertEqual(resp_completed.status_code, 200)
        self.assertContains(resp_completed, 'To finish')

    def test_delete_task(self):
        """Проверка удаления задачи"""

        u = User.objects.create_user(username='Cristiano', password='Siuuu')
        self.client.force_login(u)

        t = Todo.objects.create(user=u, title='To delete', memo='CR7')

        resp = self.client.post(reverse('deletetodo', kwargs={'todo_pk': t.pk}))
        self.assertEqual(resp.status_code, 302)

        task_exists = Todo.objects.filter(pk=t.pk).exists()
        self.assertFalse(task_exists)


class AuthRedirectTests(TestCase):
    """Неавторизованный пользователь не получает доступ к защищенным представлениям"""

    protected_urls = [
        ('createtodo', {}),
        ('currenttodos', {}),
        ('completedtodos', {}),
        ('viewtodo', {'todo_pk': 1}),
        ('completetodo', {'todo_pk': 1}),
        ('deletetodo', {'todo_pk': 1}),
    ]

    def test_anonymous_redirect_login(self):
        for url_name, kwargs in self.protected_urls:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)

            self.assertEqual(response.status_code, 302) # есть редирект

            redirect_url = response.url
            login_url = reverse('user_login')

            self.assertEqual(
                redirect_url.split('?')[0].rstrip('/'),
                login_url.rstrip('/')
            ) # есть редирект на логин

            # есть верное перенаправление после логина
            self.assertIn('next', redirect_url)
            self.assertIn(url, redirect_url)
