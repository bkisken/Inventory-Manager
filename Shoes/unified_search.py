import os
import sys
import subprocess
import json
from typing import Dict, List, Optional, Union, Any
import pandas as pd
from datetime import datetime, timedelta
import requests
import re

# Import existing modules if they're in the same directory
try:
    from stockxcaller import SneakerAPI
except ImportError:
    # If not found, define SneakerAPI class here (simplified version)
    from dataclasses import dataclass

    @dataclass
    class SneakerProduct:
        id: str
        name: str
        brand: str
        model: str
        sku: Optional[str] = None
        retail_price: Optional[float] = None
        avg_price: Optional[float] = None
        release_date: Optional[str] = None
        
        @classmethod
        def from_api_response(cls, data: Dict) -> 'SneakerProduct':
            """Create a SneakerProduct instance from API response data"""
            return cls(
                id=data.get('id', ''),
                name=data.get('title', ''),
                brand=data.get('brand', ''),
                model=data.get('slug', ''),
                sku=data.get('sku'),
                retail_price=data.get('retail_price'),
                avg_price=data.get('min_price'),
                release_date=data.get('release_date')
            )

    class SneakerAPI:
        def __init__(self):
            self.api_key = "sd_HpX6MyxuZgKhwfWE5tdMqGugtLI9pXnb"
            self.base_url = "https://api.sneakersapi.dev/api/v3/stockx"
                    
        def search_products(self, SKU: str) -> List[SneakerProduct]:
            """Search for products using SKU"""
            try:
                url = f"{self.base_url}/products"
                querystring = {"sku": SKU}
                headers = {"Authorization": self.api_key}
                response = requests.request("GET", url, headers=headers, params=querystring)
                response.raise_for_status()
                
                data = response.json()
                products = data.get('data', [])
                if products:
                    return [SneakerProduct.from_api_response(product) for product in products]
                else:
                    print("No item found in StockX")
                    return []

            except requests.RequestException as e:
                print(f"Error searching StockX for '{SKU}': {e}")
                return []
            except json.JSONDecodeError as e:
                print(f"Error parsing StockX results for '{SKU}': {e}")
                return []

# Define eBay search functions
def search_ebay(sku: str) -> Dict[str, Any]:
    """Search eBay for a SKU and return sales data"""
    try:
        # Import from ebayscrap if available
        from ebayscrap import search_shoes, calculate_metrics
        
        # Search for the SKU
        df = search_shoes(sku)
        
        # Calculate metrics if data was found
        if df is not None and not df.empty:
            metrics = calculate_metrics(df)
            return {
                'success': True,
                'data': metrics,
                'raw_data': df
            }
        else:
            return {
                'success': False,
                'message': "No eBay data found for this SKU"
            }
    except ImportError:
        # Fallback implementation if ebayscrap is not available
        return {
            'success': False,
            'message': "eBay search module not available"
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error searching eBay: {str(e)}"
        }

# Define GOAT search function
def search_goat(sku: str) -> Dict[str, Any]:
    """Search GOAT for a SKU and return price data"""
    try:
        # Since GOAT API is in JavaScript, we'll need to use Node.js to execute it
        # Check if Node.js is installed
        try:
            subprocess.run(["node", "--version"], check=True, capture_output=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            return {
                'success': False,
                'message': "Node.js not found, GOAT search unavailable"
            }
        
        # Create a temporary JavaScript file to execute the GOAT search
        temp_js_file = "temp_goat_search.js"
        with open(temp_js_file, "w") as f:
            f.write(f"""
            const goatCaller = require('./goatcaller');
            
            // Create a mock shoe object with the SKU
            const shoe = {{
                styleID: '{sku}',
                lowestResellPrice: {{}},
                resellLinks: {{}},
                resellPrices: {{}}
            }};
            
            // Call getLink to get the product
            goatCaller.getLink(shoe, (err) => {{
                if (err) {{
                    console.error(JSON.stringify({{ success: false, message: err.toString() }}));
                    process.exit(1);
                }}
                
                // Call getPrices to get the price data
                goatCaller.getPrices(shoe, (err) => {{
                    if (err) {{
                        console.error(JSON.stringify({{ success: false, message: err.toString() }}));
                        process.exit(1);
                    }}
                    
                    // Output the result as JSON
                    console.log(JSON.stringify({{ 
                        success: true, 
                        data: {{
                            lowestPrice: shoe.lowestResellPrice.goat,
                            productId: shoe.goatProductId,
                            link: shoe.resellLinks.goat,
                            prices: shoe.resellPrices.goat
                        }}
                    }}));
                    process.exit(0);
                }});
            }});
            """)
        
        # Execute the JavaScript file
        result = subprocess.run(["node", temp_js_file], capture_output=True, text=True)
        
        # Clean up
        try:
            os.remove(temp_js_file)
        except:
            pass
        
        # Parse the result
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
        else:
            return {
                'success': False,
                'message': f"GOAT search failed: {result.stderr}"
            }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error searching GOAT: {str(e)}"
        }

class UnifiedSneakerSearch:
    """A unified search class that combines StockX, eBay, and GOAT search results"""
    
    def __init__(self):
        """Initialize search APIs"""
        self.stockx_api = SneakerAPI()
    
    def search(self, sku: str) -> Dict[str, Any]:
        """
        Search across all platforms for a SKU
        
        Args:
            sku: The SKU to search for
            
        Returns:
            Dictionary containing search results from each platform
        """
        # Initialize result dictionary
        result = {
            'sku': sku,
            'timestamp': datetime.now().isoformat(),
            'stockx': None,
            'ebay': None,
            'goat': None,
            'aggregated': {
                'name': None,
                'brand': None,
                'retail_price': None,
                'avg_price': None,
                'lowest_price': None,
                'highest_price': None,
                'total_sales': 0
            }
        }
        
        # Search StockX
        stockx_products = self.stockx_api.search_products(sku)
        if stockx_products:
            product = stockx_products[0]  # Use the first product
            result['stockx'] = {
                'success': True,
                'name': product.name,
                'brand': product.brand,
                'retail_price': product.retail_price,
                'avg_price': product.avg_price
            }
            
            # Use StockX data to populate aggregated fields
            result['aggregated']['name'] = product.name
            result['aggregated']['brand'] = product.brand
            result['aggregated']['retail_price'] = product.retail_price
            result['aggregated']['avg_price'] = product.avg_price
        else:
            result['stockx'] = {
                'success': False,
                'message': "No StockX data found for this SKU"
            }
        
        # Search eBay
        ebay_result = search_ebay(sku)
        result['ebay'] = ebay_result
        
        if ebay_result.get('success', False):
            ebay_data = ebay_result['data']
            
            # Update aggregated price data with eBay information
            if ebay_data.get('average_price'):
                # If StockX data is missing, use eBay data
                if result['aggregated']['avg_price'] is None:
                    result['aggregated']['avg_price'] = ebay_data['average_price']
                # Otherwise, average the two
                else:
                    result['aggregated']['avg_price'] = (result['aggregated']['avg_price'] + ebay_data['average_price']) / 2
            
            # Update highest and lowest prices
            if ebay_data.get('highest_price'):
                if result['aggregated']['highest_price'] is None:
                    result['aggregated']['highest_price'] = ebay_data['highest_price']
                else:
                    result['aggregated']['highest_price'] = max(result['aggregated']['highest_price'], ebay_data['highest_price'])
            
            if ebay_data.get('lowest_price'):
                if result['aggregated']['lowest_price'] is None:
                    result['aggregated']['lowest_price'] = ebay_data['lowest_price']
                else:
                    result['aggregated']['lowest_price'] = min(result['aggregated']['lowest_price'], ebay_data['lowest_price'])
            
            # Update total sales count
            if ebay_data.get('total_sales'):
                result['aggregated']['total_sales'] += ebay_data['total_sales']
        
        # Search GOAT
        goat_result = search_goat(sku)
        result['goat'] = goat_result
        
        if goat_result.get('success', False):
            goat_data = goat_result['data']
            
            # Update aggregated price data with GOAT information
            if goat_data.get('lowestPrice'):
                # Update lowest price
                if result['aggregated']['lowest_price'] is None:
                    result['aggregated']['lowest_price'] = goat_data['lowestPrice']
                else:
                    result['aggregated']['lowest_price'] = min(result['aggregated']['lowest_price'], goat_data['lowestPrice'])
                
                # If average price is still missing, use the lowest price as a fallback
                if result['aggregated']['avg_price'] is None:
                    result['aggregated']['avg_price'] = goat_data['lowestPrice']
        
        return result


# Test function
def main():
    """Test the unified search function"""
    sku = input("Enter SKU to search: ")
    searcher = UnifiedSneakerSearch()
    result = searcher.search(sku)
    
    print("\nSearch Results:")
    print("=" * 50)
    
    # Print StockX results
    print("\nStockX Results:")
    if result['stockx'] and result['stockx'].get('success', False):
        print(f"Name: {result['stockx']['name']}")
        print(f"Brand: {result['stockx']['brand']}")
        print(f"Retail Price: ${result['stockx']['retail_price']}")
        print(f"Average Price: ${result['stockx']['avg_price']}")
    else:
        print("No StockX data found")
    
    # Print eBay results
    print("\neBay Results:")
    if result['ebay'] and result['ebay'].get('success', False):
        ebay_data = result['ebay']['data']
        print(f"Average Price: ${ebay_data.get('average_price', 'N/A')}")
        print(f"Last Sale Price: ${ebay_data.get('last_sale_price', 'N/A')}")
        print(f"Highest Price: ${ebay_data.get('highest_price', 'N/A')}")
        print(f"Lowest Price: ${ebay_data.get('lowest_price', 'N/A')}")
        print(f"Total Sales: {ebay_data.get('total_sales', 'N/A')}")
        print(f"Last 90 Days Sales: {ebay_data.get('last_90_days_sales', 'N/A')}")
    else:
        print("No eBay data found")
    
    # Print GOAT results
    print("\nGOAT Results:")
    if result['goat'] and result['goat'].get('success', False):
        goat_data = result['goat']['data']
        print(f"Lowest Price: ${goat_data.get('lowestPrice', 'N/A')}")
        print(f"Product Link: {goat_data.get('link', 'N/A')}")
    else:
        print("No GOAT data found")
    
    # Print aggregated results
    print("\nAggregated Results:")
    print(f"Name: {result['aggregated']['name']}")
    print(f"Brand: {result['aggregated']['brand']}")
    print(f"Retail Price: ${result['aggregated']['retail_price']}")
    print(f"Average Price: ${result['aggregated']['avg_price']}")
    print(f"Lowest Price: ${result['aggregated']['lowest_price']}")
    print(f"Highest Price: ${result['aggregated']['highest_price']}")
    print(f"Total Sales: {result['aggregated']['total_sales']}")

if __name__ == "__main__":
    main()