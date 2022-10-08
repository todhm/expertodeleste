from dataparser.numbers import round_up_decimals

class ExchangeRateDao(object): 
    exchange_rate_map = {
        "KRW-USD": 1250,
    }

    def __init__(self, original: str = "KRW", target: str = "USD", target_decimal: int = 2):
        self.exchange_rate = self.exchange_rate_map[f"{original}-{target}"]
        self.target_decimal = target_decimal
    
    def calculate_exchange_rate(self, cost: float):
        return round_up_decimals(cost / self.exchange_rate, decimals=self.target_decimal)
