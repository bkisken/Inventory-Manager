import requests
from typing import Dict, Optional, Union, List
import json
from datetime import datetime
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
            avg_price=data.get('avg_price'),
            release_date=data.get('release_date')
        )

class SneakerAPI:
    def __init__(self):
        self.api_key = "sd_HpX6MyxuZgKhwfWE5tdMqGugtLI9pXnb"
        self.base_url = "https://api.sneakersapi.dev/api/v3/stockx"

    url = "https://api.sneakersapi.dev/api/v3/stockx/products"
    headers = {"Authorization": "sd_HpX6MyxuZgKhwfWE5tdMqGugtLI9pXnb"}
            
    def search_products(self, SKU: str) -> List[SneakerProduct]:
        """
        Search for products using a query string.
        
        Args:
            SKU (str): SKU 

            
        Returns:
            List[SneakerProduct]: List of matching products
        """
        try:
            url = f"{self.base_url}/products"
            querystring = {"sku": SKU}
            headers = {"Authorization": "sd_HpX6MyxuZgKhwfWE5tdMqGugtLI9pXnb"}
            response = requests.request("GET", url, headers=headers, params=querystring)
            response.raise_for_status()
            print(response.text)
            
            data = response.json()
            # Assuming the API returns a list of products in a 'data' field
            products = data.get('data', [])
            return [SneakerProduct.from_api_response(product) for product in products]

        except requests.RequestException as e:
            print(f"Error searching for '{SKU}': {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing search results for '{SKU}': {e}")
            return []

def format_price(price: Optional[float]) -> str:
    """Format price with currency symbol and 2 decimal places"""
    if price is None:
        return "N/A"
    return f"${price:,.2f}"

def print_product(product: SneakerProduct) -> None:
    """Print formatted product information"""
    print("\nProduct Details")
    print("=" * 50)
    print(f"Name: {product.name}")
    print(f"Brand: {product.brand}")
    print(f"Model: {product.model}")
    if product.sku:
        print(f"SKU: {product.sku}")
    print(f"Retail Price: ${product.retail_price}") #retail_price is a string
    print(f"Average Price: {format_price(product.avg_price)}")
    if product.release_date:
        print(f"Release Date: {product.release_date}")
    print(f"Product ID: {product.id}")

def main():
    """Main function to demonstrate both API endpoints"""
    api = SneakerAPI()
    
    # Example 1: Get specific product
    """ 
    product_id = input("Enter product ID (or press Enter to skip): ").strip()
    if product_id:
        product = api.get_product(product_id)
        if product:
            print_product(product)
        else:
            print(f"Product not found: {product_id}")
    """
    
    # Example 2: Search for products
    search_query = input("\nEnter SKU (or press Enter to skip): ").strip()
    if search_query:
        products = api.search_products(search_query)
        if products:
            print(f"\nFound {len(products)} matching products:")
            for i, product in enumerate(products, 1):
                print(f"\nResult {i}:")
                print_product(product)
        else:
            print(f"No products found matching '{search_query}'")

if __name__ == "__main__":
    main()
