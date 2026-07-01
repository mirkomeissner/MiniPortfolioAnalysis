import src.database as database


class AssetsRepository:
    def get_all_assets_with_labels(self, isins=None):
        return database.get_all_assets_with_labels(isins)

    def search_exchange_tickers(self, isin: str | None = None, name: str | None = None, active_only: bool = True):
        return database.search_exchange_tickers(isin=isin, name=name, active_only=active_only)

    def save_asset_static_data(self, asset_data):
        return database.save_asset_static_data(asset_data)

    def update_asset_static_data(self, isin, updated_data):
        return database.update_asset_static_data(isin, updated_data)