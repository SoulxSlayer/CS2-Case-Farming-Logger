from forex_python.converter import CurrencyRates, RatesNotAvailableError

try:
    cr = CurrencyRates()
    rate = cr.get_rate('USD', 'INR')
    print(f"USD to INR rate: {rate}")
except RatesNotAvailableError as e:
    print(f"Could not get rates: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")