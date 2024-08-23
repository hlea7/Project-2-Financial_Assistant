Project # 2. Financial Assistant with Web-Interface and Databases

A Django application that provides banking services:

- сreate a user and authenticate, including logging out of the account
- perform deposit/withdraw transactions
- show transaction history
- calculate currency exchange

A more detailed description of the functionality is presented below:

1. authentication.
url: /auth

This address should output a form for authentication. Authentication is done by username and password. The built-in User model in Django is used as users. 

Without authentication, the user has no access to the functionality of the service.
After successful authentication, the user should be transferred to the main menu page (item 3).

2. Create an account.
url: /create_account

The form for creating a user should be displayed at this address
If user creation is successful, it should lead to the authentication page (item 1).

3. main menu
url: /
On this page the user can choose one of the actions.
- Balance operations
- Currency exchange
- View transaction history

4. Balance operations
url: /operations

This page should contain:
- user balance output
- a form for deposit/withdraw operations with a drop-down window for selecting the operation.

5. Currency exchange
url: /exchange

Currency conversion rates are available at: https://fake-api.apps.berlintech.ai/api/currency_exchange

This page contains a form that includes the following fields:
- input field for specifying the exchange amount
- a drop-down menu to select the currency (coefficients should be obtained from the link above).
- button to send the form.

When sending the form, the same form should be displayed, but in addition to it, the transfer data should be specified.
Currency exchange operations are not added to the history.

6. View transaction history
url: /history

This page contains a list of transactions that have been made by the user. 
Each transaction card includes:
- date in the format day/month/year hour:minutes:seconds. (example: 25/04/2024 19:12:34)
- transaction status
- balance after the operation

Description of the models that are used in this application:

User model (built-in model in Django).
History model
Fields:
    status - status of the operation (a string with possible success/failure values)
    amount - transaction amount (fractional number)
    type - type of operation (string with possible values deposit/withdraw)
    user_id - user identifier (external key to User model)
    datetime - operation date (date and time type, filled in automatically when adding a record)
