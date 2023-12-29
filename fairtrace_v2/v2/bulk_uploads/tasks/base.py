from abc import ABC, abstractmethod
from collections import defaultdict


class DataSheetAdapted(ABC):
    """
    Abstract base class for adapting data from a data sheet for processing.
    Subclasses should implement the format_data and create_data methods.
    """

    data_sheet = None  # Placeholder for the data sheet instance
    
    def __init__(self, data_sheet):
        """
        Initialize the DataSheetAdapted instance with a data sheet.

        Parameters:
        data_sheet (DataSheetUpload): The DataSheetUpload instance containing
                                      the data.
        """
        self.data = {} 
        self.errors = defaultdict(dict)  
        self.exceptions = []  
        self.data_sheet = data_sheet

    @abstractmethod
    def format_data(self):
        """
        Abstract method to format the data from the data sheet.

        This method should be implemented by subclasses to format the data from
        the data sheet in preparation for further processing or creation.
        """
        pass

    @abstractmethod
    def create_data(self):
        """
        Abstract method to create data based on the formatted data.

        This method should be implemented by subclasses to create new data or
        perform specific actions based on the formatted data.
        """
        pass


