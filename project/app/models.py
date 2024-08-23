from django.db import models
from django.contrib.auth.models import User

class History(models.Model):
    '''
    History model with the following set of fields

    status - a string with a maximum length of 10. The value are success or failure.
    The aliases are Success and Failure respectively.

    amount - a fractional number. The maximum number of digits is 10, 2 decimal places. Default value is 0.00
    
    type - a string with maximum length 10. The value must be deposit or debit.
    The aliases are Deposit and Debit respectively.
    
    user - the foreign key associated with User. The relationship type is one to many. 
    
    datetime - the point in time when the record was created.

    A string mapping of the entity in the format:
    'User Name - Transaction Type - Transaction Amount - Status'
    
    Example:
    'Tom - withdrawal - 100 - success'.
    '''
    STATUS_CHOICES = [
          ('success', 'Success'),
          ('failure', 'Failure')
    ]
    TYPE_CHOICES = [
          ('deposit', 'Deposit'),
          ('withdraw', 'Withdraw')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    datetime = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.type} - {self.amount} - {self.status}'