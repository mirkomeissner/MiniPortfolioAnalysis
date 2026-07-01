import src.database as database


class PricesRepository:
    def get_asset_prices(self):
        return database.get_asset_prices()

    def get_fx_rates(self):
        return database.get_fx_rates()