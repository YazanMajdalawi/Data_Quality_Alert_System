"""Check for missing Magento product image attributes."""
from base_check import BaseCheck
from issue import IssueCollection


class MissingProductImagesMag(BaseCheck):
    """Validates that all Magento products have image attributes set (image, small_image, thumbnail, swatch_image)."""
    
    # Image attribute codes to check
    IMAGE_ATTRIBUTES = ['image', 'small_image', 'thumbnail', 'swatch_image']
    
    def run(self):
        """
        Check for missing product image attributes.
        
        Returns:
            IssueCollection: Collection of issues found, or empty collection if none
        """
        issues = self.create_issue_collection()
        connection = None
        
        try:
            connection = self.get_magento_connection()
            
            # Use the exact query structure provided, selecting data fields instead of INSERT statements
            placeholders = ','.join(['%s'] * len(self.IMAGE_ATTRIBUTES))
            query = """
                SELECT 
                    ea.attribute_id,
                    s.store_id,
                    p.entity_id,
                    ea.attribute_code
                FROM catalog_product_entity AS p
                CROSS JOIN (SELECT 0 AS store_id UNION SELECT 1 UNION SELECT 2) AS s
                CROSS JOIN eav_attribute AS ea
                LEFT JOIN catalog_product_entity_varchar AS cpev
                    ON cpev.entity_id = p.entity_id 
                    AND cpev.attribute_id = ea.attribute_id
                    AND cpev.store_id = s.store_id
                LEFT JOIN (
                    SELECT entity_id, attribute_id, value
                    FROM catalog_product_entity_varchar
                    WHERE value IS NOT NULL
                ) AS src
                    ON src.entity_id = p.entity_id
                    AND src.attribute_id = ea.attribute_id
                WHERE ea.attribute_code IN ({})
                  AND cpev.value IS NULL
                  AND src.value IS NOT NULL
            """.format(placeholders)
            
            results = self.execute_query(connection, query, self.IMAGE_ATTRIBUTES)
            
            if results:
                # Track unique combinations for counting (attribute_id, store_id, entity_id)
                records = []
                seen_combinations = set()
                
                for row in results:
                    attribute_id, store_id, entity_id, attribute_code = row
                    
                    # Double-check: skip if any key field is NULL (shouldn't happen due to WHERE clause, but safety check)
                    if attribute_id is None or store_id is None or entity_id is None or attribute_code is None:
                        continue
                    
                    # Track unique combinations for counting
                    combination = (attribute_id, store_id, entity_id)
                    if combination not in seen_combinations:
                        seen_combinations.add(combination)
                        records.append({
                            'id': entity_id,
                            'attribute_id': attribute_id,
                            'attribute_code': attribute_code,
                            'store_id': store_id
                        })
                
                if records:
                    # Count by attribute code
                    attribute_counts = {}
                    for record in records:
                        attr_code = record['attribute_code']
                        attribute_counts[attr_code] = attribute_counts.get(attr_code, 0) + 1
                    
                    # Get unique products affected
                    unique_products = len(set(r['id'] for r in records))
                    
                    issues.add_issue(
                        check_name=self.check_name,
                        severity='medium',
                        message=f'Found {len(records)} missing product image attribute(s)',
                        details=f'Found {len(records)} missing image attribute value(s) affecting {unique_products} unique product(s)',
                        extra_data={
                            'records': records,
                            'summary': {
                                'Total missing attributes': len(records),
                                'Unique products affected': unique_products,
                                'By attribute': attribute_counts
                            }
                        }
                    )
        
        except Exception as e:
            issues.add_issue(
                check_name=self.check_name,
                severity='high',
                message='Error executing missing product images check',
                details=str(e)
            )
        
        finally:
            if connection and connection.is_connected():
                connection.close()
        
        return issues

