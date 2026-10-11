
import json
import os
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime


# ---- Exceptions ----
class BankError(Exception):
    """Base class for every error this bank can raise."""


class InvalidAmountError(BankError):
    """A deposit/withdrawal amount was zero, negative, or otherwise invalid."""


class InsufficientFundsError(BankError):
    """A withdrawal would violate an account's balance rules."""


class IncorrectPINError(BankError):
    """A login attempt failed but the account still has retries left."""


class AccountLockedError(BankError):
    """The account is locked, either already or as of this attempt."""


class AccountNotFoundError(BankError):
    """No account exists with the given account number."""


# ---- Transaction ----
class Transaction:
    """A single ledger entry belonging to an account."""

    def __init__(self, txn_type, amount, balance_after, timestamp=None):
        self.txn_type = txn_type
        self.amount = amount
        self.balance_after = balance_after
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        return {
            "type": self.txn_type,
            "amount": self.amount,
            "balance_after": self.balance_after,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["type"], data["amount"], data["balance_after"], data["timestamp"])

    def __str__(self):
        return (f"{self.timestamp}  {self.txn_type:<10} "
                f"${self.amount:>10,.2f}   balance -> ${self.balance_after:,.2f}")


# ---- Account (abstract base class) ----
class Account(ABC):
    """
    Abstract base for every account type.

    All sensitive state (`__balance`, `__pin`, ...) is private to this
    class. Subclasses never touch it directly -- they call the protected
    `_credit` / `_debit` helpers, which keeps the ledger consistent no
    matter how many account types get added later.
    """

    _next_account_number = 1001   # drives automatic account numbering
    MAX_LOGIN_ATTEMPTS = 3

    def __init__(self, name, pin, initial_deposit=0.0, *, account_number=None,
                 pin_hash=None, locked=False, failed_attempts=0, transactions=None):
        if not name or not name.strip():
            raise ValueError("Account holder name cannot be empty.")
        if initial_deposit < 0:
            raise InvalidAmountError("Initial deposit cannot be negative.")

        if account_number is None:
            self.__account_number = Account._next_account_number
            Account._next_account_number += 1
        else:
            self.__account_number = account_number
            Account._next_account_number = max(Account._next_account_number, account_number + 1)

        self.__name = name.strip()
        self.__pin = pin_hash if pin_hash is not None else self._hash_pin(pin)
        self.__balance = float(initial_deposit)
        self.__transactions = transactions if transactions is not None else []
        self.__failed_attempts = failed_attempts
        self.__locked = locked

        if initial_deposit > 0 and not self.__transactions:
            self.__record_transaction("OPENING", initial_deposit)

    # -- internal helpers -----------------------------------------------------
    @staticmethod
    def _hash_pin(pin):
        return hashlib.sha256(str(pin).encode()).hexdigest()

    def __record_transaction(self, txn_type, amount):
        self.__transactions.append(Transaction(txn_type, amount, self.__balance))

    def _validate_amount(self, amount):
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise InvalidAmountError("Amount must be a positive number.")

    def _ensure_active(self):
        if self.__locked:
            raise AccountLockedError(f"Account {self.__account_number} is locked.")

    def _credit(self, amount, txn_type="DEPOSIT"):
        """Protected: the only path by which any account's balance rises."""
        self.__balance += amount
        self.__record_transaction(txn_type, amount)

    def _debit(self, amount, txn_type="WITHDRAWAL"):
        """Protected: the only path by which any account's balance falls."""
        self.__balance -= amount
        self.__record_transaction(txn_type, amount)

    # -- public read-only interface --------------------------------------------
    @property
    def account_number(self):
        return self.__account_number

    @property
    def name(self):
        return self.__name

    @property
    def balance(self):
        return self.__balance

    @property
    def is_locked(self):
        return self.__locked

    @property
    def transactions(self):
        return list(self.__transactions)  # defensive copy, no external mutation

    # -- authentication -----------------------------------------------------------
    def login(self, pin):
        self._ensure_active()

        if self._hash_pin(pin) == self.__pin:
            self.__failed_attempts = 0
            return True

        self.__failed_attempts += 1
        if self.__failed_attempts >= self.MAX_LOGIN_ATTEMPTS:
            self.__locked = True
            raise AccountLockedError(
                f"Too many failed attempts -- account {self.__account_number} is now locked."
            )
        remaining = self.MAX_LOGIN_ATTEMPTS - self.__failed_attempts
        raise IncorrectPINError(f"Incorrect PIN. {remaining} attempt(s) remaining.")

    def unlock(self):
        """Administrative reset, e.g. after the customer verifies their identity."""
        self.__locked = False
        self.__failed_attempts = 0

    # -- transactions -----------------------------------------------------------------
    def deposit(self, amount):
        # Deposits are intentionally allowed even while locked: a lock blocks
        # the customer from using the account, not others from paying into
        # it -- the same way a frozen card can still receive funds.
        self._validate_amount(amount)
        self._credit(amount)

    @abstractmethod
    def withdraw(self, amount):
        """Each account type enforces its own withdrawal rule."""

    @abstractmethod
    def account_type(self):
        """A short label such as 'Savings' or 'Current'."""

    def mini_statement(self, count=5):
        """Return the most recent `count` transactions, oldest to newest."""
        return self.__transactions[-count:]

    # -- persistence -----------------------------------------------------------------
    def to_dict(self):
        return {
            "type": self.account_type(),
            "account_number": self.__account_number,
            "name": self.__name,
            "pin_hash": self.__pin,
            "balance": self.__balance,
            "locked": self.__locked,
            "failed_attempts": self.__failed_attempts,
            "transactions": [t.to_dict() for t in self.__transactions],
        }

    def __str__(self):
        status = "LOCKED" if self.__locked else "active"
        return (f"#{self.__account_number}  {self.__name:<18} "
                f"{self.account_type():<8} ${self.__balance:>12,.2f}  [{status}]")

    def __repr__(self):
        return f"{self.__class__.__name__}(#{self.__account_number}, {self.__name!r})"


# ---- SavingsAccount ----
class SavingsAccount(Account):
    """Earns interest; a withdrawal may never drop the balance below the minimum."""

    DEFAULT_INTEREST_RATE = 0.04
    DEFAULT_MIN_BALANCE = 500.0

    def __init__(self, name, pin, initial_deposit=0.0,
                 interest_rate=DEFAULT_INTEREST_RATE,
                 min_balance=DEFAULT_MIN_BALANCE, **kwargs):
        is_new_account = kwargs.get("transactions") is None
        if is_new_account and initial_deposit < min_balance:
            raise InvalidAmountError(
                f"Savings accounts need an opening balance of at least ${min_balance:,.2f}."
            )
        super().__init__(name, pin, initial_deposit, **kwargs)
        self.__interest_rate = interest_rate
        self.__min_balance = min_balance

    @property
    def interest_rate(self):
        return self.__interest_rate

    @property
    def min_balance(self):
        return self.__min_balance

    def withdraw(self, amount):
        self._validate_amount(amount)
        self._ensure_active()
        if self.balance - amount < self.__min_balance:
            raise InsufficientFundsError(
                f"Withdrawing ${amount:,.2f} would breach the ${self.__min_balance:,.2f} minimum."
            )
        self._debit(amount)

    def account_type(self):
        return "Savings"

    def to_dict(self):
        data = super().to_dict()
        data["interest_rate"] = self.__interest_rate
        data["min_balance"] = self.__min_balance
        return data


# ---- CurrentAccount ----
class CurrentAccount(Account):
    """A no-interest account with an overdraft cushion instead of a minimum balance."""

    DEFAULT_OVERDRAFT_LIMIT = 1000.0

    def __init__(self, name, pin, initial_deposit=0.0,
                 overdraft_limit=DEFAULT_OVERDRAFT_LIMIT, **kwargs):
        super().__init__(name, pin, initial_deposit, **kwargs)
        self.__overdraft_limit = overdraft_limit

    @property
    def overdraft_limit(self):
        return self.__overdraft_limit

    def withdraw(self, amount):
        self._validate_amount(amount)
        self._ensure_active()
        if self.balance - amount < -self.__overdraft_limit:
            raise InsufficientFundsError(
                f"Withdrawing ${amount:,.2f} would exceed the "
                f"${self.__overdraft_limit:,.2f} overdraft limit."
            )
        self._debit(amount)

    def account_type(self):
        return "Current"

    def to_dict(self):
        data = super().to_dict()
        data["overdraft_limit"] = self.__overdraft_limit
        return data


# ---- Bank ----
class Bank:
    """Owns every account and provides the operations a teller or ATM would need."""

    ACCOUNT_CLASSES = {"savings": SavingsAccount, "current": CurrentAccount}

    def __init__(self, name="My Bank"):
        self.name = name
        self._accounts = {}     # account_number -> Account
        self._numbers = []      # kept sorted, enables recursive binary search

    # -- account creation ---------------------------------------------------------
    def open_account(self, acc_type, name, pin, initial_deposit=0.0, **kwargs):
        cls = self.ACCOUNT_CLASSES.get(acc_type.lower())
        if cls is None:
            raise ValueError(f"Unknown account type '{acc_type}'.")

        account = cls(name, pin, initial_deposit, **kwargs)
        self._accounts[account.account_number] = account
        self._numbers.append(account.account_number)
        return account

    # -- lookup: recursive binary search --------------------------------------------
    def find_account(self, account_number):
        index = self._binary_search(self._numbers, account_number, 0, len(self._numbers) - 1)
        if index == -1:
            raise AccountNotFoundError(f"No account with number {account_number}.")
        return self._accounts[self._numbers[index]]

    @staticmethod
    def _binary_search(numbers, target, low, high):
        """Recursively search a sorted list of account numbers; O(log n)."""
        if low > high:
            return -1
        mid = (low + high) // 2
        if numbers[mid] == target:
            return mid
        if numbers[mid] < target:
            return Bank._binary_search(numbers, target, mid + 1, high)
        return Bank._binary_search(numbers, target, low, mid - 1)

    # -- authentication -----------------------------------------------------------------
    def login(self, account_number, pin):
        account = self.find_account(account_number)
        account.login(pin)
        return account

    # -- transfers -----------------------------------------------------------------------
    def transfer(self, sender_number, receiver_number, amount):
        if sender_number == receiver_number:
            raise ValueError("Sender and receiver cannot be the same account.")

        sender = self.find_account(sender_number)
        receiver = self.find_account(receiver_number)

        sender.withdraw(amount)        # raises and stops here if it fails
        try:
            receiver.deposit(amount)
        except BankError:
            sender.deposit(amount)     # roll back the debit so money isn't lost
            raise
        return sender, receiver

    # -- reports ------------------------------------------------------------------------
    def richest_customer(self):
        return max(self._accounts.values(), key=lambda acc: acc.balance, default=None)

    def sorted_by_balance(self, descending=True):
        return sorted(self._accounts.values(), key=lambda acc: acc.balance, reverse=descending)

    def search_by_name(self, query):
        query = query.strip().lower()
        return [acc for acc in self._accounts.values() if query in acc.name.lower()]

    # -- persistence: JSON file handling -------------------------------------------------
    def save(self, filepath="bank_data.json"):
        payload = {
            "name": self.name,
            "next_account_number": Account._next_account_number,
            "accounts": [acc.to_dict() for acc in self._accounts.values()],
        }
        try:
            with open(filepath, "w") as f:
                json.dump(payload, f, indent=2)
        except OSError as e:
            raise BankError(f"Could not save to '{filepath}': {e}")

    def load(self, filepath="bank_data.json"):
        if not os.path.exists(filepath):
            raise AccountNotFoundError(f"No saved data found at '{filepath}'.")
        try:
            with open(filepath, "r") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise BankError(f"Could not read '{filepath}': {e}")

        self.name = payload.get("name", self.name)
        self._accounts.clear()
        self._numbers.clear()

        for data in payload.get("accounts", []):
            self._accounts[data["account_number"]] = self._account_from_dict(data)
            self._numbers.append(data["account_number"])

        self._numbers.sort()
        Account._next_account_number = payload.get(
            "next_account_number", Account._next_account_number
        )

    @staticmethod
    def _account_from_dict(data):
        common = dict(
            account_number=data["account_number"],
            pin_hash=data["pin_hash"],
            locked=data["locked"],
            failed_attempts=data["failed_attempts"],
            transactions=[Transaction.from_dict(t) for t in data["transactions"]],
        )
        if data["type"] == "Savings":
            return SavingsAccount(data["name"], None, data["balance"],
                                   interest_rate=data["interest_rate"],
                                   min_balance=data["min_balance"], **common)
        if data["type"] == "Current":
            return CurrentAccount(data["name"], None, data["balance"],
                                   overdraft_limit=data["overdraft_limit"], **common)
        raise BankError(f"Unknown account type in save file: {data['type']}")


# ---- Console front-end ----
def read_float(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Please enter a valid number.")


def read_int(prompt):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Please enter a whole number.")


def print_header(title):
    print("\n" + "=" * 52)
    print(title.center(52))
    print("=" * 52)


def print_mini_statement(account):
    print(f"\nLast transactions for #{account.account_number} ({account.name}):")
    txns = account.mini_statement()
    if not txns:
        print("  (no transactions yet)")
    for txn in txns:
        print(" ", txn)
    print(f"Current balance: ${account.balance:,.2f}")


def open_account_flow(bank):
    print_header("OPEN A NEW ACCOUNT")
    name = input("Full name: ").strip()
    pin = input("Choose a PIN: ").strip()
    acc_type = input("Account type (savings/current): ").strip()
    deposit = read_float("Opening deposit: $")

    try:
        account = bank.open_account(acc_type, name, pin, deposit)
        print(f"\nAccount created! Number: {account.account_number}")
        print("Remember your account number and PIN -- both are required to log in.")
    except (BankError, ValueError) as e:
        print(f"Could not open account: {e}")


def account_menu(bank, account):
    while True:
        print_header(f"{account.name} -- {account.account_type()} #{account.account_number}")
        print("1. Check balance\n2. Deposit\n3. Withdraw\n"
              "4. Transfer money\n5. Mini statement\n6. Logout")
        choice = input("Choose an option: ").strip()

        if choice == "6":
            print("Logged out.")
            break

        try:
            if choice == "1":
                print(f"Balance: ${account.balance:,.2f}")
            elif choice == "2":
                amount = read_float("Deposit amount: $")
                account.deposit(amount)
                print(f"Deposited ${amount:,.2f}. New balance: ${account.balance:,.2f}")
            elif choice == "3":
                amount = read_float("Withdraw amount: $")
                account.withdraw(amount)
                print(f"Withdrew ${amount:,.2f}. New balance: ${account.balance:,.2f}")
            elif choice == "4":
                target = read_int("Recipient account number: ")
                amount = read_float("Amount to transfer: $")
                bank.transfer(account.account_number, target, amount)
                print(f"Sent ${amount:,.2f} to account #{target}.")
            elif choice == "5":
                print_mini_statement(account)
            else:
                print("Invalid option.")
        except BankError as e:
            print(f"Error: {e}")


def login_flow(bank):
    print_header("LOGIN")
    number = read_int("Account number: ")
    pin = input("PIN: ").strip()
    try:
        account = bank.login(number, pin)
        print("Login successful.")
        account_menu(bank, account)
    except BankError as e:
        print(f"Login failed: {e}")


def richest_customer_flow(bank):
    print_header("RICHEST CUSTOMER")
    top = bank.richest_customer()
    print(top if top else "No accounts yet.")


def sorted_accounts_flow(bank):
    print_header("ACCOUNTS BY BALANCE (highest first)")
    accounts = bank.sorted_by_balance()
    print("\n".join(str(acc) for acc in accounts) if accounts else "No accounts yet.")


def search_flow(bank):
    print_header("SEARCH BY NAME")
    query = input("Name (or part of it): ").strip()
    results = bank.search_by_name(query)
    print("\n".join(str(acc) for acc in results) if results else "No matches found.")


def main():
    bank = Bank("PyBank")
    print("Welcome to PyBank!")

    menu = (
        "\n1. Open new account\n2. Login\n3. Richest customer\n"
        "4. Accounts sorted by balance\n5. Search by name\n"
        "6. Save data\n7. Load data\n8. Exit\n"
    )

    while True:
        print(menu)
        choice = input("Choose an option: ").strip()

        if choice == "1":
            open_account_flow(bank)
        elif choice == "2":
            login_flow(bank)
        elif choice == "3":
            richest_customer_flow(bank)
        elif choice == "4":
            sorted_accounts_flow(bank)
        elif choice == "5":
            search_flow(bank)
        elif choice == "6":
            try:
                bank.save()
                print("Saved to bank_data.json.")
            except BankError as e:
                print(f"Save failed: {e}")
        elif choice == "7":
            try:
                bank.load()
                print("Data loaded.")
            except BankError as e:
                print(f"Load failed: {e}")
        elif choice == "8":
            print("Thank you for banking with PyBank. Goodbye!")
            break
        else:
            print("Invalid option, please try again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")


