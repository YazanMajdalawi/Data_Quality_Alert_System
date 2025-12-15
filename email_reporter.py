"""Email reporting functionality for data quality alerts."""
import msal
import requests
import re
from datetime import datetime
from config import EmailConfig
from issue import IssueCollection


class EmailReporter:
    """Handles email composition and sending for data quality issues."""
    
    # Configuration for formatting extra_data
    MAX_LIST_ITEMS = 10  # Maximum items to show in lists before truncation
    MAX_TABLE_ROWS = 10  # Maximum rows in tables before truncation
    
    def __init__(self):
        self.config = EmailConfig.get_config()
        self.app = msal.ConfidentialClientApplication(
            client_id=self.config['client_id'],
            client_credential=self.config['client_secret'],
            authority=f"https://login.microsoftonline.com/{self.config['tenant_id']}"
        )
    
    def format_issues(self, issues: IssueCollection, execution_info: str = None):
        """
        Format issues into a readable email body.
        
        Args:
            issues: IssueCollection object
            execution_info: Optional execution mode information to display
            
        Returns:
            str: Formatted email body (HTML)
        """
        if issues.is_empty():
            return ""
        
        # Group issues by check name using IssueCollection method
        issues_by_check = issues.group_by_check()
        
        # Build HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1 {{ color: #000000; }}
                h2 {{ color: #1976d2; margin-top: 20px; }}
                .issue {{ 
                    background-color: #fff3cd; 
                    border-left: 4px solid #ffc107; 
                    padding: 10px; 
                    margin: 10px 0; 
                }}
                .severity-high {{ border-left-color: #d32f2f; background-color: #ffebee; }}
                .severity-medium {{ border-left-color: #ff9800; background-color: #fff3e0; }}
                .severity-low {{ border-left-color: #4caf50; background-color: #e8f5e9; }}
                .details {{ margin-top: 5px; color: #333; font-size: 0.9em; }}
                .extra-data {{ margin-top: 10px; padding: 10px; background-color: #f5f5f5; border-radius: 4px; }}
                .extra-data-section {{ margin-top: 10px; }}
                .extra-data-title {{ font-weight: bold; color: #1976d2; margin-bottom: 5px; }}
                .extra-data-list {{ margin: 5px 0; padding-left: 20px; }}
                .extra-data-list li {{ margin: 3px 0; }}
                .extra-data-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.9em; }}
                .extra-data-table th {{ background-color: #1976d2; color: white; padding: 8px; text-align: left; }}
                .extra-data-table td {{ padding: 6px 8px; border-bottom: 1px solid #ddd; }}
                .extra-data-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .truncation-notice {{ margin-top: 5px; font-style: italic; color: #666; font-size: 0.85em; }}
                .execution-info {{ color: #999; font-size: 0.85em; font-style: italic; margin-top: 5px; }}
            </style>
        </head>
        <body>
            <h1>Data Quality Alert Report</h1>
            <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Total Issues Found:</strong> {len(issues)}</p>
        """
        
        # Add execution info if provided
        if execution_info:
            html_body += f'<p class="execution-info">Execution mode: {execution_info}</p>\n'
        
        for check_name, check_issues in issues_by_check.items():
            formatted_name = self._format_check_name(check_name)
            html_body += f'<h2>{formatted_name}</h2>\n'
            for issue in check_issues:
                severity_class = f"severity-{issue.severity}"
                html_body += f"""
                <div class="issue {severity_class}">
                    <strong>[{issue.severity.upper()}]</strong> {issue.message}
                """
                # Add details if present
                if issue.details:
                    html_body += f'<div class="details">{issue.details}</div>'
                # Add extra_data if present
                if issue.has_extra_data():
                    html_body += self._format_extra_data(issue.extra_data)
                html_body += "</div>\n"
        
        html_body += """
        <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
        <p style="color: #666; font-size: 0.9em; margin-top: 20px;">Yazan Majdalawi</p>
        </body>
        </html>
        """
        
        return html_body
    
    def _format_extra_data(self, extra_data):
        """
        Format extra_data into HTML.
        
        Args:
            extra_data: Dictionary containing structured data
            
        Returns:
            str: HTML formatted extra_data
        """
        html = '<div class="extra-data">'
        
        # Format entity_ids
        if 'entity_ids' in extra_data and extra_data['entity_ids']:
            html += self._format_list(
                extra_data['entity_ids'],
                'Entity IDs',
                self.MAX_LIST_ITEMS
            )
        
        # Format invalid_values
        if 'invalid_values' in extra_data and extra_data['invalid_values']:
            html += self._format_list(
                extra_data['invalid_values'],
                'Invalid Values',
                self.MAX_LIST_ITEMS
            )
        
        # Format records (tabular data)
        if 'records' in extra_data and extra_data['records']:
            html += self._format_table(
                extra_data['records'],
                self.MAX_TABLE_ROWS
            )
        
        # Format summary
        if 'summary' in extra_data and extra_data['summary']:
            html += self._format_summary(extra_data['summary'])
        
        html += '</div>'
        return html
    
    def _format_list(self, items, title, max_items):
        """Format a list of items with truncation."""
        html = f'<div class="extra-data-section">'
        html += f'<div class="extra-data-title">{title}:</div>'
        html += '<ul class="extra-data-list">'
        
        total_count = len(items)
        display_items = items[:max_items]
        
        for item in display_items:
            html += f'<li>{self._escape_html(str(item))}</li>'
        
        html += '</ul>'
        
        if total_count > max_items:
            html += f'<div class="truncation-notice">Showing first {max_items} of {total_count} items</div>'
        
        html += '</div>'
        return html
    
    def _format_table(self, records, max_rows):
        """Format records as an HTML table with truncation."""
        if not records:
            return ''
        
        html = '<div class="extra-data-section">'
        html += '<div class="extra-data-title">Detailed Records:</div>'
        html += '<table class="extra-data-table">'
        
        # Get column headers from first record
        headers = list(records[0].keys())
        html += '<thead><tr>'
        for header in headers:
            html += f'<th>{self._escape_html(str(header))}</th>'
        html += '</tr></thead>'
        
        # Add rows
        html += '<tbody>'
        total_count = len(records)
        display_records = records[:max_rows]
        
        for record in display_records:
            html += '<tr>'
            for header in headers:
                value = record.get(header, '')
                html += f'<td>{self._escape_html(str(value))}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
        
        if total_count > max_rows:
            html += f'<div class="truncation-notice">Showing first {max_rows} of {total_count} records</div>'
        
        html += '</div>'
        return html
    
    def _format_summary(self, summary):
        """Format summary statistics."""
        html = '<div class="extra-data-section">'
        html += '<div class="extra-data-title">Summary:</div>'
        html += '<ul class="extra-data-list">'
        
        for key, value in summary.items():
            html += f'<li><strong>{self._escape_html(str(key))}:</strong> {self._escape_html(str(value))}</li>'
        
        html += '</ul></div>'
        return html
    
    def _format_check_name(self, check_name):
        """Format check name by inserting spaces before capital letters."""
        # Insert space before capital letters (but not before the first one)
        formatted = re.sub(r'(?<!^)(?=[A-Z])', ' ', check_name)
        return formatted
    
    def _escape_html(self, text):
        """Escape HTML special characters."""
        if not isinstance(text, str):
            text = str(text)
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))
    
    def _get_access_token(self):
        """Get access token using MSAL."""
        result = self.app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" in result:
            return result["access_token"]
        else:
            raise Exception(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
    
    def send_email(self, issues: IssueCollection, execution_info: str = None):
        """
        Send email with data quality issues via Microsoft Graph API.
        
        Args:
            issues: IssueCollection object
            execution_info: Optional execution mode information to display
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if issues.is_empty():
            return False
        
        try:
            # Get access token
            access_token = self._get_access_token()
            
            # Create email message
            html_body = self.format_issues(issues, execution_info)
            
            # Format recipients
            recipients = [{"emailAddress": {"address": email}} for email in self.config['recipients']]
            
            message = {
                "message": {
                    "subject": f'Data Quality Alert - {len(issues)} Issue(s) Found',
                    "body": {
                        "contentType": "HTML",
                        "content": html_body
                    },
                    "toRecipients": recipients
                }
            }
            
            # Send email via Microsoft Graph API
            url = f"https://graph.microsoft.com/v1.0/users/{self.config['sender']}/sendMail"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=message, headers=headers)
            response.raise_for_status()
            
            return True
        
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def _format_issues_text(self, issues: IssueCollection):
        """Format issues as plain text (fallback for email clients)."""
        if issues.is_empty():
            return ""
        
        text = f"Data Quality Alert Report\n"
        text += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"Total Issues Found: {len(issues)}\n\n"
        
        # Group by check name using IssueCollection method
        issues_by_check = issues.group_by_check()
        
        for check_name, check_issues in issues_by_check.items():
            text += f"{check_name}:\n"
            text += "-" * len(check_name) + "\n"
            for issue in check_issues:
                text += f"  [{issue.severity.upper()}] {issue.message}\n"
                if issue.details:
                    text += f"    Details: {issue.details}\n"
                text += "\n"
        
        return text

