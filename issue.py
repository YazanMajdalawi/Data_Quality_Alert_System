"""Issue and IssueCollection classes for data quality checks."""
from typing import Optional, Dict, List


class Issue:
    """Represents a single data quality issue."""
    
    VALID_SEVERITIES = {'low', 'medium', 'high'}
    
    def __init__(self, check_name: str, severity: str, message: str, 
                 details: Optional[str] = None, extra_data: Optional[Dict] = None):
        """
        Initialize an Issue.
        
        Args:
            check_name: Name of the check that found this issue
            severity: Severity level ('low', 'medium', or 'high')
            message: Brief description of the issue
            details: Additional details about the issue (optional)
            extra_data: Optional structured data for detailed reporting
        """
        self.check_name = check_name
        self.severity = severity
        self.message = message
        self.details = details if details is not None else ""
        self.extra_data = extra_data if extra_data else {}
        
        # Validate on creation
        self.validate()
    
    def validate(self):
        """Validate that the issue has required fields and valid values."""
        if not self.check_name:
            raise ValueError("check_name is required")
        if not self.severity:
            raise ValueError("severity is required")
        if self.severity not in self.VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {self.VALID_SEVERITIES}, got '{self.severity}'")
        if not self.message:
            raise ValueError("message is required")
    
    def has_extra_data(self) -> bool:
        """Check if extra_data exists and is non-empty."""
        return bool(self.extra_data)


class IssueCollection:
    """Container for multiple Issue objects."""
    
    def __init__(self):
        """Initialize an empty IssueCollection."""
        self.issues: List[Issue] = []
    
    def add_issue(self, check_name: str, severity: str, message: str, 
                  details: Optional[str] = None, extra_data: Optional[Dict] = None) -> 'IssueCollection':
        """
        Add an issue to the collection (builder pattern).
        
        Args:
            check_name: Name of the check
            severity: Severity level
            message: Brief description
            details: Additional details (optional)
            extra_data: Optional structured data
            
        Returns:
            self for method chaining
        """
        issue = Issue(check_name, severity, message, details, extra_data)
        self.issues.append(issue)
        return self
    
    def filter_by_severity(self, severity: str) -> 'IssueCollection':
        """
        Filter issues by severity level.
        
        Args:
            severity: Severity level to filter by
            
        Returns:
            New IssueCollection with filtered issues
        """
        filtered = IssueCollection()
        filtered.issues = [issue for issue in self.issues if issue.severity == severity]
        return filtered
    
    def group_by_check(self) -> Dict[str, List[Issue]]:
        """
        Group issues by check_name.
        
        Returns:
            Dictionary mapping check_name to list of issues
        """
        grouped = {}
        for issue in self.issues:
            if issue.check_name not in grouped:
                grouped[issue.check_name] = []
            grouped[issue.check_name].append(issue)
        return grouped
    
    def count_by_severity(self) -> Dict[str, int]:
        """
        Count issues by severity level.

        Returns:
            Dictionary mapping severity to count, e.g. {'low': 0, 'medium': 0, 'high': 0}
        """
        counts = {'low': 0, 'medium': 0, 'high': 0}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts
    
    def get_summary(self) -> Dict:
        """
        Get aggregated statistics about the collection.
        
        Returns:
            Dictionary with summary statistics
        """
        return {
            'total_issues': len(self.issues),
            'by_severity': self.count_by_severity(),
            'by_check': {name: len(issues) for name, issues in self.group_by_check().items()},
            'unique_checks': len(self.group_by_check())
        }
    
    def is_empty(self) -> bool:
        """Check if the collection is empty."""
        return len(self.issues) == 0
    
    def extend(self, other: 'IssueCollection'):
        """
        Add all issues from another IssueCollection.
        
        Args:
            other: Another IssueCollection to merge
        """
        self.issues.extend(other.issues)
    
    def __iter__(self):
        """Make the collection iterable."""
        return iter(self.issues)
    
    def __len__(self) -> int:
        """Get the count of issues."""
        return len(self.issues)
    
    def __repr__(self) -> str:
        """String representation of the collection."""
        return f"IssueCollection({len(self.issues)} issues)"

