import csv
import pickle
import json
import os  # Додаємо для безпечного пошуку конфігурації (як на Рисунку 13)


# ==========================================
# 1. СТРУКТУРА КАТЕГОРІЙ ТА БАЗОВІ КЛАСИ
# ==========================================
class Category:
    FOOD = "FOOD"
    TRANSPORT = "TRANSPORT"
    SALARY = "SALARY"
    ENTERTAINMENT = "ENTERTAINMENT"


class Transaction:
    def __init__(self, category: str, amount: float):
        if amount <= 0:
            raise ValueError("Сума транзакції повинна бути більшою за нуль!")
        self.category = category
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def __add__(self, other):
        if isinstance(other, (int, float)):
            return self.amount + other
        return self.amount + other.amount

    def __radd__(self, other):
        return self.__add__(other)


class Income(Transaction):
    def __str__(self) -> str:
        return f"Income('{self.category}', amount={self.amount})"


class Expense(Transaction):
    def __str__(self) -> str:
        return f"Expense('{self.category}', amount={self.amount})"


# ==========================================
# 2. ФУНКТОР ТА КАСТОМНИЙ ІТЕРАТОР
# ==========================================
class FinanceAnalytics:
    def __init__(self):
        self.total_analyzed_amount = 0.0
        self.call_count = 0

    def __call__(self, transaction: Transaction) -> float:
        self.call_count += 1
        self.total_analyzed_amount += transaction.amount
        
        if isinstance(transaction, Expense):
            return round(transaction.amount * 0.015, 2)
        return 0.0


class ExpenseFilterIterator:
    def __init__(self, transactions: list):
        self._transactions = transactions
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self) -> Expense:
        while self._index < len(self._transactions):
            current_tx = self._transactions[self._index]
            self._index += 1
            if isinstance(current_tx, Expense):
                return current_tx
        raise StopIteration


# ==========================================
# 3. КЛАС-МЕНЕДЖЕР (БЕКАП, CSV ТА JSON)
# ==========================================
class Wallet:
    # ---------------------------------------------------------
    # Рисунок 11: Атрибути для зберігання налаштувань
    # ---------------------------------------------------------
    def __init__(self, initial_balance: float = 0.0):
        self.balance = initial_balance
        self.transactions = []
        self.analyzer = FinanceAnalytics()
        
        # Налаштування за замовчуванням (точно як у зразку)
        self.company_name = "Nexus Dev Financial"
        self.page_size = 5

    # ---------------------------------------------------------
    # ЗАВДАННЯ «Завантаження налаштувань» (JSON)
    # ---------------------------------------------------------
    def load_config(self, filename: str):
        """Завантажує конфігураційні налаштування трекера з файлу JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                config = json.load(file)
                
                # Читаємо параметри (безпечно, з дефолтними значеннями)
                self.company_name = config.get("company_name", "Nexus Dev Financial")
                self.page_size = config.get("page_size", 5)
                
                print(f"[JSON] Налаштування успішно завантажено.")
                print(f"[JSON] Компанія: '{self.company_name}', Розмір сторінки: {self.page_size}")
        except FileNotFoundError:
            print(f"[JSON Помилка] Файл '{filename}' не знайдено! Залишено базові налаштування.")

    # ---------------------------------------------------------
    # Рисунок 14: Використання завантажених параметрів у генераторі
    # ---------------------------------------------------------
    def generate_statement_pages(self):
        """Генератор сторінок, який використовує self.page_size з конфігу"""
        for i in range(0, len(self.transactions), self.page_size):
            yield self.transactions[i:i + self.page_size]

    # ---------------------------------------------------------
    # ЗАВДАННЯ «Повний бекап системи» (PICKLE)
    # ---------------------------------------------------------
    def save_to_pickle(self, file_path: str):
        with open(file_path, 'wb') as f:
            pickle.dump(self, f)
        print(f"[Pickle] Повний бекап системи збережено у файл '{file_path}'")

    @staticmethod
    def load_from_pickle(file_path: str):
        with open(file_path, 'rb') as f:
            wallet_instance = pickle.load(f)
        print(f"[Pickle] Стан системи успішно відновлено з файлу '{file_path}'")
        return wallet_instance

    # ---------------------------------------------------------
    # ЗАВДАННЯ «Табличний звіт» (CSV)
    # ---------------------------------------------------------
    def export_to_csv(self, file_path: str):
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Тип Транзакції", "Категорія", "Сума (UAH)"])
            
            for tx in self.transactions:
                tx_type = "Дохід (Income)" if isinstance(tx, Income) else "Витрата (Expense)"
                writer.writerow([tx_type, tx.category, tx.amount])
                
        print(f"[CSV] Табличний звіт успішно експортовано у файл '{file_path}'")

    def add_transaction(self, transaction: Transaction):
        fee = self.analyzer(transaction)
        
        if isinstance(transaction, Income):
            self.balance += transaction.amount
        elif isinstance(transaction, Expense):
            total_deduction = transaction.amount + fee
            if self.balance < total_deduction:
                raise ValueError(f"Недостатньо коштів разом з комісією ({total_deduction})!")
            self.balance -= total_deduction
            
        self.transactions.append(transaction)


# ==========================================
# 4. КОНТЕКСТНИЙ МЕНЕДЖЕР СЕСІЇ
# ==========================================
class FinancialSession:
    def __init__(self, wallet: Wallet):
        self.wallet = wallet
        self.status = "Not Started"

    def __enter__(self):
        self.status = "Active"
        self._snapshot_balance = self.wallet.balance
        self._snapshot_transactions = list(self.wallet.transactions)
        print("\n=== [Сесія] Фінансову сесію відкрито ===")
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type is not None:
            self.status = "Rolled Back"
            self.wallet.balance = self._snapshot_balance
            self.wallet.transactions = self._snapshot_transactions
            print(f"[Сесія Помилка] {exc_val}. Виконано відкат змін!")
            return True
            
        self.status = "Committed"
        print("[Сесія Успіх] Сесію закрито. Зміни збережено в ОЗП.")
        return True


# ==========================================
# 5. ТЕСТУВАННЯ РОБОТИ ПРОГРАМИ
# ==========================================
if __name__ == "__main__":
    print("--- Крок 0: Завантаження початкових конфігурацій проекту з JSON ---")
    my_wallet = Wallet(initial_balance=12000.0)
    
    # Рисунок 13: Динамічне та безпечне формування шляху до файлу налаштувань
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    my_wallet.load_config(config_path)

    print("\n--- Крок 1: Додавання фінансових операцій ---")
    with FinancialSession(my_wallet) as session:
        my_wallet.add_transaction(Income(Category.SALARY, 6000.0))
        my_wallet.add_transaction(Expense(Category.FOOD, 350.0))
        my_wallet.add_transaction(Expense(Category.TRANSPORT, 80.0))
        my_wallet.add_transaction(Expense(Category.ENTERTAINMENT, 2000.0))

    print(f"\nПоточний баланс до очищення пам'яті: {my_wallet.balance} UAH")

    print("\n--- Крок 2: Експорт даних у CSV для Excel ---")
    my_wallet.export_to_csv("transactions_report.csv")

    print("\n--- Крок 3: Створення повного бекапу системи через Pickle ---")
    my_wallet.save_to_pickle("wallet_backup.bin")

    print("\n==========================================================")
    print("ІМІТАЦІЯ ПЕРЕЗАПУСКУ ПРОГРАМИ (del my_wallet)")
    print("==========================================================")
    del my_wallet
    
    print("\n--- Крок 4: Відновлення об'єкта з файлу wallet_backup.bin ---")
    restored_wallet = Wallet.load_from_pickle("wallet_backup.bin")
    
    print(f"\n[Результат] Відновлений баланс: {restored_wallet.balance} UAH")
    print(f"[Результат] Відновлено транзакцій: {len(restored_wallet.transactions)}")
    print(f"[Результат] Лічильник викликів функтора аналітики: {restored_wallet.analyzer.call_count}")

    print(f"\n--- Крок 5: Перевірка роботи генератора сторінок (Розмір сторінки з JSON = {restored_wallet.page_size}) ---")
    # Метод тепер викликається без параметрів, бо автоматично бере self.page_size
    page_gen = restored_wallet.generate_statement_pages()
    page_num = 1
    for page in page_gen:
        print(f"Сторінка звітів №{page_num}: {[str(tx) for tx in page]}")
        page_num += 1