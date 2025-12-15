"""Check for invalid cities in Magento customer addresses."""
from base_check import BaseCheck
from issue import IssueCollection


class CityValidationMag(BaseCheck):
    """Validates that all cities in Magento customer addresses are from the allowed list."""
    
    # Valid cities list
    VALID_CITIES = [
        'Baghdad', 'Karbala', 'Babel', 'Diwaniyah', 'Najaf', 'Basra',
        'Maysan', 'Saladin', 'Anbar', 'Dhi Qar', 'Wasit', 'Muthanna',
        'Kirkuk', 'Sulaymaniyah', 'Erbil', 'Dohuk', 'Nineveh', 'Diyala', 'Halabja'
    ]
    
    def run(self):
        """
        Check for invalid cities in customer addresses.
        
        Returns:
            IssueCollection: Collection of issues found, or empty collection if none
        """
        issues = self.create_issue_collection()
        connection = None
        
        try:
            connection = self.get_magento_connection()
            
            # Build the query with parameterized valid cities
            # Check for invalid cities, NULL cities, and empty cities
            placeholders = ','.join(['%s'] * len(self.VALID_CITIES))
            query = """
                SELECT entity_id, city
                FROM customer_address_entity
                WHERE (city NOT IN ({}) OR city IS NULL OR city = '')
                ORDER BY entity_id
            """.format(placeholders)
            
            results = self.execute_query(connection, query, self.VALID_CITIES)
            
            if results:
                # Separate results by type
                invalid_city_records = []
                null_city_records = []
                empty_city_records = []
                
                for row in results:
                    entity_id, city = row
                    if city is None:
                        null_city_records.append({'id': entity_id, 'city': '(NULL)'})
                    elif city == '':
                        empty_city_records.append({'id': entity_id, 'city': '(Empty)'})
                    else:
                        invalid_city_records.append({'id': entity_id, 'city': city})
                
                # Issue for invalid city names
                if invalid_city_records:
                    invalid_cities = sorted(set(r['city'] for r in invalid_city_records))
                    issues.add_issue(
                        check_name=self.check_name,
                        severity='medium',
                        message=f'Found {len(invalid_cities)} invalid city name(s) in customer addresses',
                        details=f'Found {len(invalid_cities)} unique invalid city name(s) affecting {len(invalid_city_records)} address record(s)',
                        extra_data={
                            'invalid_values': invalid_cities,
                            'records': invalid_city_records,
                            'summary': {
                                'Unique invalid cities': len(invalid_cities),
                                'Affected addresses': len(invalid_city_records)
                            }
                        }
                    )
                
                # Issue for NULL cities
                if null_city_records:
                    issues.add_issue(
                        check_name=self.check_name,
                        severity='medium',
                        message=f'Found {len(null_city_records)} address(es) with NULL city value',
                        details=f'Found {len(null_city_records)} address record(s) with NULL city value',
                        extra_data={
                            'records': null_city_records,
                            'summary': {
                                'NULL cities': len(null_city_records)
                            }
                        }
                    )
                
                # Issue for empty cities
                if empty_city_records:
                    issues.add_issue(
                        check_name=self.check_name,
                        severity='medium',
                        message=f'Found {len(empty_city_records)} address(es) with empty city value',
                        details=f'Found {len(empty_city_records)} address record(s) with empty city value',
                        extra_data={
                            'records': empty_city_records,
                            'summary': {
                                'Empty cities': len(empty_city_records)
                            }
                        }
                    )
        
        except Exception as e:
            issues.add_issue(
                check_name=self.check_name,
                severity='high',
                message='Error executing city validation check',
                details=str(e)
            )
        
        finally:
            if connection and connection.is_connected():
                connection.close()
        
        return issues

