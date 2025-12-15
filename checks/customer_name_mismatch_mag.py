"""Check for mismatched customer names between customer_entity and customer_address_entity."""
from base_check import BaseCheck
from issue import IssueCollection


class CustomerNameMismatchMag(BaseCheck):
    """Validates that customer names in addresses match the names in customer entity."""
    
    def run(self):
        """
        Check for mismatched customer names between customer_entity and customer_address_entity.
        
        Returns:
            IssueCollection: Collection of issues found, or empty collection if none
        """
        issues = self.create_issue_collection()
        connection = None
        
        try:
            connection = self.get_magento_connection()
            
            query = """
                SELECT
                    ce.entity_id          AS customer_id,
                    ce.firstname          AS customer_firstname,
                    ce.lastname           AS customer_lastname,
                    cae.entity_id         AS address_id,
                    cae.firstname         AS address_firstname,
                    cae.lastname          AS address_lastname
                FROM customer_entity AS ce
                JOIN customer_address_entity AS cae
                    ON cae.parent_id = ce.entity_id
                WHERE
                    ce.firstname <> cae.firstname
                 OR ce.lastname <> cae.lastname
                ORDER BY ce.entity_id, cae.entity_id
            """
            
            results = self.execute_query(connection, query)

            
            # results.append((999, 'John', 'Doe', 1999, 'Johnny', 'Doel'))  # test row
            if results:
                # Convert results to records format
                records = [
                    {
                        'customer_id': row[0],
                        'customer_firstname': row[1] if row[1] else '(NULL)',
                        'customer_lastname': row[2] if row[2] else '(NULL)',
                        'address_id': row[3],
                        'address_firstname': row[4] if row[4] else '(NULL)',
                        'address_lastname': row[5] if row[5] else '(NULL)'
                    }
                    for row in results
                ]
                
                # Get unique customers affected
                unique_customers = len(set(r['customer_id'] for r in records))
                
                issues.add_issue(
                    check_name=self.check_name,
                    severity='medium',
                    message=f'Found {len(records)} address(es) with mismatched customer names',
                    details=f'Found {len(records)} address record(s) where customer name does not match the customer entity name, affecting {unique_customers} unique customer(s)',
                    extra_data={
                        'records': records,
                        'summary': {
                            'Total mismatched addresses': len(records),
                            'Unique customers affected': unique_customers
                        }
                    }
                )
        
        except Exception as e:
            issues.add_issue(
                check_name=self.check_name,
                severity='high',
                message='Error executing customer name mismatch check',
                details=str(e)
            )
        
        finally:
            if connection and connection.is_connected():
                connection.close()
        
        return issues

