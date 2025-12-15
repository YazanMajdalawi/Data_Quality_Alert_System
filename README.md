# Data Quality Alert System

An automated data quality monitoring system that runs validation checks against Magento and ERP databases and sends email alerts when issues are found.

## Features

- **Modular Design**: Easy to add new check scripts
- **Auto-Discovery**: Automatically finds and runs all check scripts
- **Consolidated Reporting**: Sends a single email with all issues found
- **Database Support**: Connects to both Magento and ERP MySQL databases
- **Configurable**: Uses environment variables for secure configuration

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your database and email credentials.

3. **Run the System**
   ```bash
   python manager.py
   ```

## Adding New Checks

To add a new data quality check:

1. Create a new Python file in the `checks/` directory
2. Create a class that inherits from `BaseCheck`
3. Implement the `run()` method that returns an `IssueCollection`

Example:

```python
from base_check import BaseCheck

class MyNewCheck(BaseCheck):
    def run(self):
        issues = self.create_issue_collection()
        
        # Your validation logic here
        # If issues found, use the builder pattern:
        issues.add_issue(
            check_name=self.check_name,
            severity='medium',  # 'low', 'medium', or 'high'
            message='Brief description',
            details='Additional details',  # Optional
            extra_data={  # Optional: structured data for detailed reporting
                'invalid_values': ['value1', 'value2'],  # List of invalid values
                'records': [  # Tabular data (each dict is a row)
                    {'id': 1, 'name': 'Record 1', 'status': 'invalid'},
                    {'id': 2, 'name': 'Record 2', 'status': 'invalid'}
                ],
                'summary': {'total': 10, 'invalid': 2}  # Summary statistics
            }
        )
        
        return issues
```

The manager will automatically discover and run your new check.

## Issue Structure

Checks return an `IssueCollection` object containing `Issue` objects. Each issue has:

- `check_name`: Name of the check (automatically set) - **Required**
- `severity`: 'low', 'medium', or 'high' (validated automatically) - **Required**
- `message`: Brief description of the issue - **Required**
- `details`: Additional details about the issue (optional)
- `extra_data`: (optional) Dictionary with structured data for detailed reporting:
  - `invalid_values`: List of invalid values found
  - `records`: List of dictionaries (each dict is a row for tabular display)
  - `summary`: Dictionary with summary statistics or counts

### IssueCollection Methods

The `IssueCollection` class provides useful methods:

- `add_issue()`: Builder pattern - add an issue and return self for chaining
- `filter_by_severity(severity)`: Filter issues by severity level
- `group_by_check()`: Group issues by check_name (returns dict)
- `count_by_severity()`: Return counts by severity
- `get_summary()`: Get aggregated statistics
- `is_empty()`: Check if collection is empty
- `extend(other)`: Add all issues from another IssueCollection
- `__len__()`: Get count of issues
- `__iter__()`: Iterate over issues

The email reporter automatically formats `extra_data` into tables, lists, and summaries with appropriate truncation. Checks only need to provide the raw data - formatting is handled by the system.

## BaseCheck Helper Methods

The `BaseCheck` class provides helper methods:

### Database Connections
- `get_magento_connection()`: Get connection to Magento database
- `get_erp_connection()`: Get connection to ERP database
- `execute_query(connection, query, params=None)`: Execute a SQL query

### Issue Management
- `create_issue_collection()`: Create a new empty `IssueCollection` for your check

## Email Configuration

The system sends emails via Microsoft Graph API using MSAL authentication. Configure your Microsoft Azure app credentials in `.env`:
- `MSAL_CLIENT_ID`: Your Azure app client ID
- `MSAL_CLIENT_SECRET`: Your Azure app client secret
- `MSAL_TENANT_ID`: Your Azure tenant ID
- `EMAIL_SENDER`: The email address that will send the alerts
- `EMAIL_RECIPIENTS`: Comma-separated list of recipient email addresses
- The email is only sent if issues are found

## Example Checks

See the following example checks:
- `checks/city_validation_mag.py` - Validates city names in Magento customer addresses
- `checks/missing_product_images_mag.py` - Checks for missing product image attributes in Magento

