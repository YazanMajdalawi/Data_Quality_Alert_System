"""Base class for all data quality check scripts."""
from abc import ABC, abstractmethod
import mysql.connector
from mysql.connector import Error
from config import DatabaseConfig
from issue import IssueCollection


class BaseCheck(ABC):
    """Abstract base class for all data quality checks."""
    
    def __init__(self):
        self.check_name = self.__class__.__name__
        self.magento_config = DatabaseConfig.get_magento_config()
        self.erp_config = DatabaseConfig.get_erp_config()
    
    @abstractmethod
    def run(self) -> IssueCollection:
        """
        Execute the check and return an IssueCollection.
        
        Returns:
            IssueCollection: Collection of issues found. Returns empty IssueCollection if no issues found.
        """
        pass
    
    def create_issue_collection(self) -> IssueCollection:
        """
        Create a new IssueCollection for this check.
        
        Returns:
            IssueCollection: New empty collection
        """
        return IssueCollection()
    
    def get_magento_connection(self):
        """
        Get a connection to the Magento database.
        
        Returns:
            mysql.connector.connection.MySQLConnection: Database connection object
            
        Raises:
            Error: If connection fails
        """
        try:
            connection = mysql.connector.connect(**self.magento_config)
            return connection
        except Error as e:
            raise Error(f"Failed to connect to Magento database: {e}")
    
    def get_erp_connection(self):
        """
        Get a connection to the ERP database.
        
        Returns:
            mysql.connector.connection.MySQLConnection: Database connection object
            
        Raises:
            Error: If connection fails
        """
        try:
            connection = mysql.connector.connect(**self.erp_config)
            return connection
        except Error as e:
            raise Error(f"Failed to connect to ERP database: {e}")
    
    def execute_query(self, connection, query, params=None):
        """
        Execute a SQL query and return results.
        
        Args:
            connection: MySQL connection object
            query: SQL query string
            params: Optional parameters for parameterized queries
            
        Returns:
            list: List of tuples containing query results
        """
        cursor = connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            return results
        finally:
            cursor.close()

