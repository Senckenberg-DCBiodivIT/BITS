class DataProvider:
    """
    Template class for a data provider.

    This class can be extended to implement specific data provider logic.
    """

    def __init__(self):
        """
        Initialize the DataProvider.
        """
        self.common_config = {}
        self.role = ""

    def load_config(self, common_config: dict, config_file: dict, role: str):
        """
        Load the configuration for the data provider.
        """
        self.common_config = common_config
        self.role = role

        self.common_config["internal_config"][self.role] = {}

    def load_data(self):
        """
        Load data from the data source.

        Returns:
            Any: The loaded data.
        """
        pass

    def save_data(self, data):
        """
        Save data to the data source.

        Args:
            data (Any): The data to save.
        """
        pass