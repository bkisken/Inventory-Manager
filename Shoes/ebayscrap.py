import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re

# eBay filters as specified
ebay_filters = {
    "item_conditions": {
        "New": 1000,
        "Open box": 1500,
        "Used": 3000,
        "Certified Refurbished": 2000,
        "Excellent - Refurbished": 2500,
        "Very Good": 3000,
        "Good": 4000,
        "For Parts or Not Working": 7000
    },
    "directories": {
        "Clothing, Shoes & Accessories": 11450
    },
    "subdirectories": {
        "Men's Shoes": 93427
    }
} #add mroe filters and test as you go to make sure your on the right track iteratively thsi will help narrow it down

#dig into the code blow more and just check at every step, just ot understand whats going on below. whether printing out the files, or examining fields, working from
#simpler HTMl page is good then expan for complexity

'''
def search_shoes(sku):
    url = "https://www.ebay.com/sch/i.html"
    search_query = f" {sku}  " #check formatting for sku this could be off

    # Search parameters including eBay filters
    params = {
        '_nkw': search_query,
        'LH_Complete': '1',
        'LH_Sold': '1',
        '_ipg': '100',
        '_dcat': ebay_filters["directories"]["Clothing, Shoes & Accessories"],
    }

    items_list = []
    page_number = 1

    while True:
        params['_pgn'] = page_number
        response = requests.get(url, params=params)  
       # print(response)
        soup = BeautifulSoup(response.text, 'html.parser')
       # print(f"Response Content: {response.text}")

       #D print(soup.prettify())


        items = soup.find_all('div', class_='s-item__wrapper clearfix')
        if not items:
            break


#issue in loop here parsing the items data, this is where I'll want to test each part, digging into why getting no results found, understand why we are getting different skus
#possibly diff skus above and no results found is below possibly not making the proper request and getting mroe than we want. We know that theres some issue below
#go throuhg step by step and make sure your getting what you want
        for item in items:
            title_tag = item.find('h3', class_='s-item__title')
        
            if title_tag:
                print(title_tag)
                title = title_tag.get_text(strip=True)

                if re.search(f"{re.escape(sku)}", title, re.I):
                    price = item.find('span', class_='s-item__price').get_text(strip=True)
                    link = item.find('a', class_='s-item__link')['href']
                    date_str = item.find('span', class_='s-item__ended-date').get_text(strip=True) if item.find('span', class_='s-item__ended-date') else None
                    date = parse_date(date_str) if date_str else None
                    items_list.append({
                        'Title': title,
                        'Price': price,
                        'Link': link,
                        'Date': date
                    })

        next_button = soup.find('a', attrs={'aria-label': 'Next page'})
        if next_button and 'disabled' not in next_button.attrs:
            page_number += 1
        else:
            break

    return pd.DataFrame(items_list)
'''

def search_shoes(sku):
    url = "https://www.ebay.com/sch/i.html"
    search_query = (sku)


    params = {
        '_nkw': search_query,
        'LH_Complete': '1',
        'LH_Sold': '1',
        '_ipg': '100',
        '_dcat': ebay_filters["directories"]["Clothing, Shoes & Accessories"],
    }

    items_list = []
    page_number = 1
    sku_clean = re.sub(r'[\W_]+', '', sku.lower())

   
    while True:
        params['_pgn'] = page_number
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('li', class_='s-item')  # updated to reflect eBay structure

           

        elif response.status_code != 200:
            print(f"Request failed with status {response.status_code}")
            break
        
        next_button = soup.find('a', attrs={'aria-label': 'Next page'})
        if next_button and 'disabled' not in next_button.attrs:
            page_number += 1
            
      
        for item in items:
            title_tag = item.find('h3', class_='s-item__title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                title_clean = re.sub(r'[\W_]+', '', title.lower())

                if sku_clean in title_clean:
                    price_tag = item.find('span', class_='s-item__price')
                    link_tag = item.find('a', class_='s-item__link')
                    date_tag = item.find('span', class_='s-item__ended-date')

                    price = price_tag.get_text(strip=True) if price_tag else '0'
                    link = link_tag['href'] if link_tag else ''
                    date_str = date_tag.get_text(strip=True) if date_tag else None
                    date = parse_date(date_str) if date_str else None

                    items_list.append({
                        'Title': title,
                        'Price': price,
                        'Link': link,
                        'Date': date
                    })
        if not items:
            print("No items found on this page.")
            break

        else:
            break
    print(items)
    return pd.DataFrame(items_list)




def parse_date(date_str):
    try:
        return pd.to_datetime(date_str)
    except:
        return None

def clean_price(price_str):
    """Convert price string to float"""
    try:
        price = re.sub(r'[^\d.]', '', price_str)
        return float(price)
    except:
        return 0.0
    


def calculate_metrics(df):
    """Calculate sales metrics"""
    if df.empty:
        return None
    


    df['Price_Clean'] = df['Price'].apply(clean_price)
    metrics = {
        'average_price': round(df['Price_Clean'].mean(), 2),
        'last_sale_price': round(df['Price_Clean'].iloc[0], 2),
        'highest_price': round(df['Price_Clean'].max(), 2),
        'lowest_price': round(df['Price_Clean'].min(), 2),
        'total_sales': len(df),
        'last_90_days_sales': len(df[df['Date'] >= (datetime.now() - timedelta(days=90))])
    }
    return metrics

def main():
    sku = "DH6931-001"

    df = search_shoes(sku)
    if df.empty:
        print("No results found") #THIS IS WHERE TEST IS FAILING
    else:
      #  print(df)
        metrics = calculate_metrics(df)
        if metrics:
            print("\nSales Metrics:")
            for key, value in metrics.items():
                print(f"{key.capitalize()}: {value}")

if __name__ == "__main__":
    main()
