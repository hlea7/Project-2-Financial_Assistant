from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.template.loader import render_to_string
from unittest.mock import patch
from bs4 import BeautifulSoup
from django.db.utils import IntegrityError
from .models import History  
from .views import *
from .forms import CreateUserForm

class BalanceCalculationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser')

    def test_get_balance_empty_history(self):
        balance = getBalance(self.user)
        self.assertEqual(balance, 0.0)

    def test_get_balance_with_transactions(self):
        History.objects.create(user=self.user, amount=100, type='deposit', status='success')
        History.objects.create(user=self.user, amount=50, type='withdraw', status='success')
        History.objects.create(user=self.user, amount=25, type='deposit', status='success')
        expected_balance = 100 + 25 - 50
        balance = getBalance(self.user)
        
        self.assertEqual(balance, expected_balance)

class CurrencyParamsTestCase(TestCase):
    @patch('requests.get')
    def test_get_currency_params_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'AUD': 1.62,
            'CAD': 1.48,
            'CHF': 1.08,
            'EUR': 1.0,
            'GBP': 0.88,
            'JPY': 129.5,
            'USD': 1.15
        }


        data, currency_choices = getCurrencyParams()

        self.assertIsNotNone(data)
        self.assertIsNotNone(currency_choices)
        self.assertIsInstance(data, dict)
        self.assertIsInstance(currency_choices, list)
        self.assertEqual(len(currency_choices), 7)

        expected_currency_choices = [
            ('AUD', 'AUD (1.62)'), ('CAD', 'CAD (1.48)'), ('CHF', 'CHF (1.08)'),
            ('EUR', 'EUR (1.0)'), ('GBP', 'GBP (0.88)'), ('JPY', 'JPY (129.5)'),
            ('USD', 'USD (1.15)')
        ]
        self.assertEqual(currency_choices, expected_currency_choices)

class CreateUserViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.create_user_url = reverse('create_account')

    def test_create_user_view_get(self):
        response = self.client.get(self.create_user_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/create_account.html')
        self.assertIsInstance(response.context['form'], CreateUserForm)

    @patch('app.views.User.objects.create_user')
    def test_create_user_view_post(self, mock_create_user):
        mock_create_user.return_value = User.objects.create_user(username='testuser', password='testpassword')
        data = {
            'username': 'testuser',
            'password1': 'testpassword',
            'password2': 'testpassword',
        }
        response = self.client.post(self.create_user_url, data)
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_create_user_view_context_authenticated(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.create_user_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['username'], 'testuser')

class CustomLoginViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')

    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/login.html')

    def test_login_view_post_success(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        data = {
            'username': 'testuser',
            'password': 'testpassword',
        }
        response = self.client.post(self.login_url, data)
        self.assertRedirects(response, reverse('main_menu'))

    def test_login_view_post_invalid_credentials(self):
        data = {
            'username': 'invaliduser',
            'password': 'invalidpassword',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200) 
        self.assertContains(response, 'Please enter a correct username and password.')

    def test_login_view_context_authenticated(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['username'], 'testuser')


class MainMenuViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.main_menu_url = reverse('main_menu') 

    def test_main_menu_view_get_authenticated(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.main_menu_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/main_menu.html')
        self.assertEqual(response.context['username'], 'testuser')

    def test_main_menu_view_get_unauthenticated(self):
        response = self.client.get(self.main_menu_url)
        self.assertEqual(response.status_code, 302) 


class BalanceOperationsViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.operations_url = reverse('operations') 

    def test_balance_operations_view_get(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.operations_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/operations.html')
        self.assertIn('balance', response.context)
        self.assertEqual(response.context['username'], 'testuser')

    def test_balance_operations_view_post_deposit(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        data = {
            'amount': '100',
            'operation': 'deposit',
        }
        response = self.client.post(self.operations_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(History.objects.filter(user=user).count(), 1)
        self.assertEqual(History.objects.filter(user=user, status='success').count(), 1)

    def test_balance_operations_view_post_withdraw_success(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        History.objects.create(user=user, amount=100, type='deposit', status='success')
        self.client.force_login(user)
        data = {
            'amount': '50',
            'operation': 'withdraw',
        }
        response = self.client.post(self.operations_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(History.objects.filter(user=user).count(), 2)
        self.assertEqual(History.objects.filter(user=user, status='success').count(), 2)

    def test_balance_operations_view_post_withdraw_failure(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        History.objects.create(user=user, amount=100, type='deposit', status='success')
        self.client.force_login(user)
        data = {
            'amount': '150',
            'operation': 'withdraw',
        }
        response = self.client.post(self.operations_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(History.objects.filter(user=user, status='failure').count(), 1)

    def test_balance_operations_view_login_required(self):
        response = self.client.get(self.operations_url)
        self.assertEqual(response.status_code, 302)  

        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.operations_url)
        self.assertEqual(response.status_code, 200)  

class ViewTransactionHistoryViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.history_url = reverse('history')

    def test_transaction_history_view_login_required(self):
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 302)

        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)

    def test_transaction_history_view_context(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/history.html')
        self.assertIn('transactions', response.context)
        self.assertEqual(len(response.context['transactions']), 0)

        History.objects.create(user=user, amount=100, type='deposit', status='success')
        History.objects.create(user=user, amount=50, type='withdraw', status='success')

        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['transactions']), 2) 


class ViewTransactionHistoryViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.history_url = reverse('history')

    def test_transaction_history_view_login_required(self):
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 302) 

        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)

    def test_transaction_history_view_context(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/history.html')
        self.assertIn('transactions', response.context)
        self.assertEqual(len(response.context['transactions']), 0)

        History.objects.create(user=user, amount=100, type='deposit', status='success')
        History.objects.create(user=user, amount=50, type='withdraw', status='success')

        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['transactions']), 2) 

    def test_transaction_history_view_only_user_transactions(self):
        user1 = User.objects.create_user(username='testuser1', password='testpassword1')
        user2 = User.objects.create_user(username='testuser2', password='testpassword2')
        self.client.force_login(user1)

        History.objects.create(user=user1, amount=100, type='deposit', status='success')
        History.objects.create(user=user2, amount=50, type='withdraw', status='success')

        response = self.client.get(self.history_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['transactions']), 1) 


class CurrencyExchangeViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.exchange_url = reverse('currency_exchange')

    def test_currency_exchange_view_get(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.get(self.exchange_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/currency_exchange.html')
        self.assertIn('currency_choices', response.context)
        self.assertIsNone(response.context['amount'])
        self.assertIsNone(response.context['currency'])
        self.assertIsNone(response.context['exchanged_amount'])

    def test_currency_exchange_view_post_with_data(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.post(self.exchange_url, {'amount': 100, 'currency': 'USD'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/currency_exchange.html')
        self.assertIn('currency_choices', response.context)
        self.assertEqual(response.context['amount'], 100)
        self.assertEqual(response.context['currency'], 'USD')
        self.assertIsNotNone(response.context['exchanged_amount'])
        self.assertIsInstance(response.context['exchanged_amount'], float)

    def test_currency_exchange_view_post_invalid_amount(self):
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(user)
        response = self.client.post(self.exchange_url, {'amount': 'invalid', 'currency': 'USD'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app/currency_exchange.html')
        self.assertIn('currency_choices', response.context)
        self.assertIsNone(response.context['amount'])
        self.assertIsNone(response.context['currency'])
        self.assertIsNone(response.context['exchanged_amount'])


class CurrencyExchangeTemplateTestCase(TestCase):
    def test_currency_choices_rendering(self):
        currency_choices = [('USD', 'USD (1.0)'), ('EUR', 'EUR (0.85)'), ('GBP', 'GBP (0.72)')]
        context = {'currency_choices': currency_choices}

        rendered = render_to_string('app/currency_exchange.html', context)

        for currency, label in currency_choices:
            self.assertInHTML(f'<option value="{currency}">{label}</option>', rendered)

    def test_transaction_details_rendering(self):
        context = {'amount': 100, 'currency': 'EUR', 'exchanged_amount': 85}

        rendered = render_to_string('app/currency_exchange.html', context)

        self.assertInHTML('<p><strong>Amount:</strong> 100</p>', rendered)
        self.assertInHTML('<p><strong>Currency:</strong> EUR</p>', rendered)
        self.assertInHTML('<p><strong>Exchanged Amount:</strong> 85</p>', rendered)


class TransactionHistoryTemplateTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        History.objects.create(user=self.user, status='success', amount=100)
        History.objects.create(user=self.user, status='failure', amount=50)
        History.objects.create(user=self.user, status='success', amount=75)


    def test_transaction_history_rendering(self):
        transactions = History.objects.all()
        context = {'transactions': transactions}
        rendered = render_to_string('app/history.html', context)

        for transaction in transactions:
            self.assertInHTML(f'Date: {transaction.datetime.strftime("%d/%m/%Y %H:%M:%S")}', rendered)
            self.assertInHTML(f'Status: {transaction.status}', rendered)
            self.assertInHTML(f'Balance After: {transaction.amount}', rendered)

    def test_empty_transaction_history_rendering(self):
        context = {'transactions': []}
        rendered = render_to_string('app/history.html', context)
        self.assertInHTML('<li class="list-group-item">No transactions found.</li>', rendered)


class MainMenuTemplateTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')

    def test_main_menu_links_authenticated(self):
        client = Client()
        client.force_login(self.user)
        main_menu_url = reverse('main_menu')
        response = client.get(main_menu_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        list_group = soup.find('ul', class_='list-group')
        links = list_group.find_all('a')
        expected_links = [
            reverse('operations'), reverse('currency_exchange'), reverse('history')
        ]
        self.assertEqual(len(set(links)), 3)
        for link in links:
            self.assertIn(link['href'], expected_links)


class BalanceOperationsTemplateTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')


    def test_balance_operations_balance_nonzero(self):
        client = Client()
        History.objects.create(status='success', amount=100, type='deposit', user=self.user)
        History.objects.create(status='failure', amount=50, type='withdraw', user=self.user)
        client.force_login(self.user)
        balance_operations_url = reverse('operations')
        response = client.get(balance_operations_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Your current balance: ${100}')

    def test_balance_operations_balance_zero(self):
        client = Client()
        client.force_login(self.user)
        balance_operations_url = reverse('operations')
        response = client.get(balance_operations_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You have a zero balance')


class HistoryModelConstraintsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser', password='testpassword')

    def test_max_digits_amount(self):
        with self.assertRaises(Exception):
            History.objects.create(
                status='success',
                amount=100000000000,
                type='deposit',
                user=self.user
            )
    def test_foreign_key_user(self):
        with self.assertRaises(IntegrityError):
            History.objects.create(
                status='success',
                amount=100.00,
                type='deposit'
            )
