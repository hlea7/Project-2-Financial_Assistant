from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.db.models import Sum
from django.views.generic import CreateView, TemplateView, View, ListView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from .models import History
from .forms import CreateUserForm
import requests

def logout_view(request):
    logout(request)
    return redirect('login') 

def getBalance(user):
    '''
    A function finds the user's balance and returns it with the float data type. 
    To calculate the balance, it calculates the sum of all user's deposits and the sum of all withdrawals.
    Then subtract the withdrawal amount from the deposit amount and return the result.
    '''
    deposits_sum = History.objects.filter(user=user,type='deposit',status='success').aggregate(Sum('amount'))['amount__sum']
    withdrawals_sum = History.objects.filter(user=user,type='withdraw',status='success').aggregate(Sum('amount'))['amount__sum']

    if deposits_sum is None:
        deposits_sum = 0
    if withdrawals_sum is None:
        withdrawals_sum = 0

    balance_result = deposits_sum - withdrawals_sum

    return float(balance_result)

def getCurrencyParams():
    '''
    A function that makes a GET request to the following address 
    https://fake-api.apps.berlintech.ai/api/currency_exchange

    if the response code is 200 it returns a list of two values:
    - a dictionary of data that came from the server
    - a list of strings based on the received data 
    mask to form the string f'{currency} ({rate})'.
    example string: 'USD (1.15)'

    if the server response code is not 200 it 
    returns the list [None, None]
    '''
    currency_url = 'https://fake-api.apps.berlintech.ai/api/currency_exchange'

    try:
        response = requests.get(currency_url)
        if response.status_code == 200:
            data = response.json()
            string_list = [(currency,f'{currency} ({rate})') for currency,rate in data.items()]
            return [data, string_list]
        else:
            return [None, None]
    except Exception as e:
        print(e)
        return [None, None]


class CreateUserView(CreateView):
    '''
    This class creates a new user.
    The model is the User model
    The CreateUserForm model is used as a form.
    The file create_account.html is used as a template.
    If the account is successfully created, it redirects to the page with the name login
    '''
    model = User
    template_name = 'app/create_account.html'
    form_class = CreateUserForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        # Save the new user 
        form.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        # If the form is invalid, re-render the page with existing data
        return self.render_to_response(self.get_context_data(form=form))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        '''
        If the user is authenticated, it adds the 'username' key with the value of username to the context.
        '''
        if self.request.user.is_authenticated:
            context['username'] = self.request.user.username
        return context

class CustomLoginView(LoginView):
    '''
    Specified the login.html file as the template
    If authentication is positive, redirect to main_menu page
    '''
    template_name = 'app/login.html'
    success_url = reverse_lazy('main_menu')

    def get_success_url(self):
        return self.success_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        '''
        If the user is authenticated, it adds the 'username' key with the value of username to the context.
        '''
        if self.request.user.is_authenticated:
            context['username'] = self.request.user.username
        return context

class MainMenuView(LoginRequiredMixin, TemplateView):
    template_name = 'app/main_menu.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        '''
        If the user is authenticated, it adds the 'username' key with the value of username to the context.
        '''
        if self.request.user.is_authenticated:
            context['username'] = self.request.user.username
        return context

class BalanceOperationsView(LoginRequiredMixin, View):
    template_name = 'app/operations.html'
    
    def get(self, request):
        '''
        This method returns the page given in template_name with a context.

        Context is a dictionary with balance and username keys.
        The balance key contains the result of the getBalance function
        username contains the username of the user.
        '''
        context = {}  
        context['balance'] = getBalance(request.user)
        context['username'] = request.user.username
        return render(request, self.template_name, context) 

    def post(self, request):
        '''
        This method processes a balance transaction.
        It adds an entry to the History model. 
        
        status - if the amount on the account is not enough when attempting to withdraw funds, the status is failure, otherwise withdraw
        amount - amount of operation, obtained from the form
        type - type of operation (withdraw/deposit), the value is obtained from the form.
        user - object of the current user

        This method returns the page given in template_name with a context.

        Context is a dictionary with balance and username keys.
        The balance key contains the result of the getBalance function (after account update)
        username contains the username of the user.
        '''            
        type = request.POST.get('operation')
        amount = float(request.POST.get('amount'))        
        balance = getBalance(request.user)
        if type == 'withdraw':
            if balance >= amount:
                status = 'success'
                balance -= amount
                amount = str(amount)
                messages.success(request, f"Amount: {amount} was withdrawn")
            else:
                messages.error(request, "Insufficient balance")
                status = 'failure'
        elif type == 'deposit':
            status = 'success'
            balance += amount
            amount = str(amount)
            messages.success(request, f"Amount: {amount} was deposited")

        History.objects.create(
            status=status,
            amount=amount,
            type=type,
            user=request.user
        )
        
        getBalance(request.user)  # Call the function to update the balance

        context = {
            'balance': balance,
            'username': request.user.username
        }
        return render(request, self.template_name, context)

class ViewTransactionHistoryView(LoginRequiredMixin, ListView):
    model = History
    template_name = 'app/history.html'
    context_object_name = 'transactions'
    ordering = ['-datetime']

    def get_queryset(self):
        '''
        This method returns the entire transaction history of the current user
        '''
        return History.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        '''
        Addd the 'username' key with the value of username to the context.
        '''
        context['username'] = self.request.user.username
        return context

class CurrencyExchangeView(LoginRequiredMixin, View):
    template_name = 'app/currency_exchange.html'
    empty_context = {'currency_choices': [], 'amount': None, 'currency': None, 'exchanged_amount': None}

    def get(self, request):
        _, currency_choices = getCurrencyParams()
        '''
        Generates a context variable with all values from empty_context and the converted values of currency_choices and username
        currency_choices contains the value of the currency_choices variable
        username contains the name of the current user
        '''
        context = {
            **self.empty_context, 
            'currency_choices': currency_choices,  
            'username': self.request.user.username
        }
        return render(request, self.template_name, context)

    def post(self, request):
        data, currency_choices = getCurrencyParams()
        '''
            This method:
            1) contains the process of forming the variable amount.
            If the amount value from the form is converted to float type, then assign it to the amount variable. Otherwise, it is None.
            2) contains a currency variable that contains the currency value from the form.
            3) if the variables data or amount contains None, it returns page with empty context (empty_context). Otherwise, performs the following steps
            4) generates the exchange_rate variable by calculating the corresponding value from the data variable
            5) generates the exchanged_amount variable, which contains the converted currency to two decimal places.
            6) forms a context from the previously created variables and returns a template with it.
        '''
        amount = request.POST.get('amount')
        try:
            amount = float(amount) if amount else None
        except ValueError:
            amount = None  # Set to None if conversion fails
        currency = request.POST.get('currency')
        if data is None or amount is None:
            context = self.empty_context
            return render(request, self.template_name, context)
        exchange_rate = data.get(currency) 
        if exchange_rate is not None:
            exchanged_amount = round(amount * exchange_rate, 2)
        else:
            exchanged_amount = None  # Handle case where exchange rate is not found            
        context = {
            'currency_choices': currency_choices,
            'amount': amount,
            'currency': currency,
            'exchanged_amount': exchanged_amount,
            'username': request.user.username
        }    
        return render(request, self.template_name, context)
