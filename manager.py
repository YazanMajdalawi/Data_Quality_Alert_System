"""Manager script that discovers and executes all data quality check scripts."""
import os
import argparse
import importlib
import importlib.util
import sys
from pathlib import Path
from email_reporter import EmailReporter
from issue import IssueCollection
from config import CheckConfig


class CheckManager:
    """Manages discovery and execution of data quality check scripts."""
    
    def __init__(self, checks_dir='checks'):
        self.checks_dir = checks_dir
        self.issues = IssueCollection()
        self.execution_mode = None
        self.execution_info = None
    
    def discover_checks(self):
        """
        Discover all check scripts in the checks directory.
        
        Returns:
            tuple: (list of check class instances, dict mapping file names to class names)
        """
        checks = []
        file_to_class_map = {}
        checks_path = Path(self.checks_dir)
        
        if not checks_path.exists():
            print(f"Warning: Checks directory '{self.checks_dir}' not found")
            return checks, file_to_class_map
        
        # Get all Python files in checks directory
        for file_path in checks_path.glob('*.py'):
            # Skip __init__.py
            if file_path.name == '__init__.py':
                continue
            
            try:
                # Import the module
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(
                    module_name,
                    file_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find classes that inherit from BaseCheck
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        attr_name != 'BaseCheck' and
                        hasattr(attr, '__bases__')):
                        # Check if it inherits from BaseCheck
                        for base in attr.__bases__:
                            if base.__name__ == 'BaseCheck':
                                check_instance = attr()
                                checks.append(check_instance)
                                # Map file name to class name
                                file_to_class_map[module_name] = check_instance.check_name
                                print(f"Loaded check: {check_instance.check_name}")
                                break
            
            except Exception as e:
                print(f"Error loading check from {file_path.name}: {e}")
        
        return checks, file_to_class_map
    
    def _resolve_check_name(self, check_name: str, all_checks: list, 
                           file_to_class_map: dict) -> str:
        """
        Resolve a check name (class name or file name) to the actual class name.
        
        Args:
            check_name: User-provided check name (class name or file name)
            all_checks: List of all discovered check instances
            file_to_class_map: Dictionary mapping file names to class names
            
        Returns:
            Class name if found, None otherwise
        """
        check_name_lower = check_name.lower()
        
        for check in all_checks:
            # Match by class name (case-insensitive)
            if check.check_name.lower() == check_name_lower:
                return check.check_name
        
        # Match by file name (case-insensitive)
        for file_name, class_name in file_to_class_map.items():
            if file_name.lower() == check_name_lower:
                return class_name
        
        return None
    
    def _get_disabled_check_names(self, all_checks: list, 
                                  file_to_class_map: dict) -> set:
        """
        Resolve disabled check names from configuration to actual class names.
        
        Args:
            all_checks: List of all discovered check instances
            file_to_class_map: Dictionary mapping file names to class names
            
        Returns:
            set: Set of disabled check class names
        """
        disabled_config = CheckConfig.get_disabled_checks()
        if not disabled_config:
            return set()
        
        disabled_class_names = set()
        for disabled_name in disabled_config:
            resolved = self._resolve_check_name(disabled_name, all_checks, file_to_class_map)
            if resolved:
                disabled_class_names.add(resolved)
        
        return disabled_class_names
    
    def filter_checks(self, all_checks: list, file_to_class_map: dict,
                     include_names: list = None, exclude_names: list = None) -> tuple:
        """
        Filter checks based on include/exclude criteria and disabled checks configuration.
        
        Args:
            all_checks: List of all discovered check instances
            file_to_class_map: Dictionary mapping file names to class names
            include_names: List of check names to include (if provided, only these run)
            exclude_names: List of check names to exclude
            
        Returns:
            Tuple of (filtered_checks, execution_info_string)
        """
        if include_names and exclude_names:
            raise ValueError("Cannot use both --checks and --exclude at the same time")
        
        # Get disabled checks from configuration
        disabled_class_names = self._get_disabled_check_names(all_checks, file_to_class_map)
        
        # Track disabled checks that were requested via --checks
        requested_disabled = []
        
        if include_names:
            # Include mode: only run specified checks
            filtered = []
            resolved_names = []
            not_found = []
            
            for name in include_names:
                resolved = self._resolve_check_name(name, all_checks, file_to_class_map)
                if resolved:
                    # Check if this check is disabled
                    if resolved in disabled_class_names:
                        requested_disabled.append(resolved)
                    else:
                        resolved_names.append(resolved)
                else:
                    not_found.append(name)
            
            if not_found:
                print(f"Warning: Could not find checks: {', '.join(not_found)}")
            
            if requested_disabled:
                formatted_disabled = ', '.join([self._format_check_name(name) for name in requested_disabled])
                print(f"Warning: The following checks are disabled and will be skipped: {formatted_disabled}")
            
            for check in all_checks:
                if check.check_name in resolved_names:
                    filtered.append(check)
            
            if not filtered:
                if requested_disabled:
                    return [], f"No valid checks found from: {', '.join(include_names)} (requested checks are disabled)"
                return [], f"No valid checks found from: {', '.join(include_names)}"
            
            formatted_names = ', '.join([self._format_check_name(name) for name in resolved_names])
            info = f"Selected checks executed: {formatted_names}"
            if requested_disabled:
                formatted_disabled = ', '.join([self._format_check_name(name) for name in requested_disabled])
                info += f" (disabled checks skipped: {formatted_disabled})"
            return filtered, info
        
        elif exclude_names:
            # Exclude mode: run all except specified
            filtered = []
            excluded_names = []
            not_found = []
            
            for name in exclude_names:
                resolved = self._resolve_check_name(name, all_checks, file_to_class_map)
                if resolved:
                    excluded_names.append(resolved)
                else:
                    not_found.append(name)
            
            if not_found:
                print(f"Warning: Could not find checks to exclude: {', '.join(not_found)}")
            
            # Filter out both excluded and disabled checks
            for check in all_checks:
                if check.check_name not in excluded_names and check.check_name not in disabled_class_names:
                    filtered.append(check)
            
            excluded_formatted = []
            if excluded_names:
                excluded_formatted.append(', '.join([self._format_check_name(name) for name in excluded_names]))
            if disabled_class_names:
                disabled_formatted = ', '.join([self._format_check_name(name) for name in disabled_class_names])
                excluded_formatted.append(f"disabled: {disabled_formatted}")
            
            if excluded_formatted:
                info = f"All checks executed except: {', '.join(excluded_formatted)}"
            else:
                info = "All checks executed"
            
            return filtered, info
        
        else:
            # Default: run all checks except disabled ones
            filtered = []
            for check in all_checks:
                if check.check_name not in disabled_class_names:
                    filtered.append(check)
            
            if disabled_class_names:
                formatted_disabled = ', '.join([self._format_check_name(name) for name in disabled_class_names])
                info = f"All checks executed (disabled checks skipped: {formatted_disabled})"
            else:
                info = "All checks executed"
            
            return filtered, info
    
    def _format_check_name(self, check_name: str) -> str:
        """Format check name by inserting spaces before capital letters."""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', ' ', check_name)
    
    def run_checks(self, include_names: list = None, exclude_names: list = None):
        """
        Run discovered checks and collect issues.
        
        Args:
            include_names: List of check names to run (include mode)
            exclude_names: List of check names to skip (exclude mode)
        """
        all_checks, file_to_class_map = self.discover_checks()
        
        if not all_checks:
            print("No checks found to run")
            return
        
        # Filter checks based on include/exclude
        checks, self.execution_info = self.filter_checks(
            all_checks, file_to_class_map, include_names, exclude_names
        )
        
        if not checks:
            print("No checks to run after filtering")
            return
        
        print(f"\nRunning {len(checks)} check(s)...\n")
        
        for check in checks:
            try:
                print(f"Running {check.check_name}...")
                check_issues = check.run()
                self.issues.extend(check_issues)
                
                if not check_issues.is_empty():
                    print(f"  Found {len(check_issues)} issue(s)")
                else:
                    print(f"  No issues found")
            
            except Exception as e:
                print(f"  Error running {check.check_name}: {e}")
                self.issues.add_issue(
                    check_name=check.check_name,
                    severity='high',
                    message='Error executing check',
                    details=str(e)
                )
        
        print(f"\nTotal issues found: {len(self.issues)}")
    
    def send_report(self):
        """Send email report if issues were found."""
        if self.issues.is_empty():
            print("\nNo issues found. No email will be sent.")
            return
        
        print("\nSending email report...")
        reporter = EmailReporter()
        success = reporter.send_email(self.issues, execution_info=self.execution_info)
        
        if success:
            print("Email sent successfully")
        else:
            print("Failed to send email")


def main():
    """Main entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Run data quality checks and send email alerts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manager.py                                    # Run all checks
  python manager.py --checks CityValidationMag          # Run only CityValidationMag
  python manager.py --checks city_validation_mag       # Same, using file name
  python manager.py --exclude CityValidationMag         # Run all except CityValidationMag
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--checks',
        nargs='+',
        metavar='CHECK',
        help='Run only the specified checks (can use class name or file name)'
    )
    group.add_argument(
        '--exclude',
        nargs='+',
        metavar='CHECK',
        help='Run all checks except the specified ones (can use class name or file name)'
    )
    
    args = parser.parse_args()
    
    # Add checks directory to path for imports
    checks_dir = Path(__file__).parent / 'checks'
    if str(checks_dir) not in sys.path:
        sys.path.insert(0, str(checks_dir.parent))
    
    manager = CheckManager()
    manager.run_checks(
        include_names=args.checks,
        exclude_names=args.exclude
    )
    manager.send_report()


if __name__ == '__main__':
    main()

