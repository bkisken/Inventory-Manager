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
        "Men's Shoes": 93427,
        "Women's Shoes": 3034
    }
} #add mroe filters and test as you go to make sure your on the right track iteratively thsi will help narrow it down

#dig into the code blow more and just check at every step, just ot understand whats going on below. whether printing out the files, or examining fields, working from
#simpler HTMl page is good then expan for complexity

#have hard coded examples in case ebay or stockx website crashes

def search_shoes(sku):
    url = "https://www.ebay.com/sch/i.html" #this is the ebay HTML that is being searched for the data
    search_query = (sku) #the search query currnetly is only based on the SKU


    params = {
        '_nkw': search_query,
        'LH_Complete': '1',
        'LH_Sold': '1',
        '_ipg': '100',
        '_dcat': ebay_filters["directories"]["Clothing, Shoes & Accessories"],
    }


    items_list = []
    page_number = 1 #this is set up to begin taking items form the first page
    sku_clean = re.sub(r'[\W_]+', '', sku.lower())

   
    while True:
        params['_pgn'] = page_number
        response = requests.get(url, params=params)
        print(response.url)
        
        if response.status_code == 200:
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('li', class_='s-item')  # updated to reflect eBay structure
  

        elif response.status_code != 200:
            print(f"Request failed with status {response.status_code}")
            break
        
        next_button = soup.find('a', attrs={'aria-label': 'Next page'})
        if next_button and 'disabled' not in next_button.attrs:
            page_number += 1
       # print(items)
    #make stripped down verion of HTML
    #ould open in a browser maybe higher up get
    #add as many tests as possible


        for item in items:
            title_tag = item.find('div', class_="s-item__title")
           
            if title_tag:
                title = title_tag.get_text(strip=True)
                title_clean = re.sub(r'[\W_]+', '', title.lower())
                

                if sku_clean in title_clean:
                    price_tag = item.find('span', class_='s-item__price')
                    link_tag = item.find('a', class_='s-item__link')
                    date = None
                    sold_info = item.find('span', class_='s-item__title--tagblock')
                    if sold_info:
                        sold_text = sold_info.get_text(strip=True)
                        match = re.search(r'Sold\s+(\d+)\s+day', sold_text)
                        if match:
                            days_ago = int(match.group(1))
                            date = datetime.now() - timedelta(days=days_ago)

                    price = price_tag.get_text(strip=True) if price_tag else '0'
                    link = link_tag['href'] if link_tag else ''
            
                    items_list.append({
                        'Title': title,
                        'Price': price,
                        'Link': link,
                        'Date': date
                    })
                  
        if not items:
            print("No items found on this page.")
            break
#regular expression for 2 becasue, to break it down in to 3 different words, so just grab first one
#missing row
        else:
            break
    #print(items)
   # return pd.DataFrame(items_list)
    df= pd.DataFrame(items_list, columns=["Title", "Price", "Link", "Date"])
    return df




#def parse_date(date_str):
 #   try:
  #      return pd.to_datetime(date_str)
 #   except:
   #     return None

def clean_price(price_str): # if you get a 0 it is likely because of this clean price is off
    """Extract and clean the first float-looking price from a string like '$150.00 to $199.99'"""
    try:
        match = re.search(r'\$?([\d,]+\.?\d*)', price_str)
        if match:
            price = match.group(1).replace(',', '')
            return float(price)
    except:
        pass
    return 0.0
    


def calculate_metrics(df):
    """Calculate sales metrics"""
    print(df)
    if df.empty:
        return None
    
    #df['Price_Clean'] = df['Price'].apply(clean_price)
    #df = df[df['Price_Clean'] > 0]  # Filter out bad price rows
    
    #see what its pulling 0 for, can force to pull closest non 0 number, idx or iloc, get more info about lowest, it may be when your reading soem of the tags 
    # there may be additonal tag corresponding to some other leement


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
    
    sku = input("Enter SKU (primary search term): ")
        # brand = input("Enter brand (optional, press enter to skip): ") or None
        #model = input("Enter model (optional, press enter to skip): ") or None
        #size = input("Enter size (optional, press enter to skip): ") or None
        #condition = input("Enter condition (New/Used, default=Used): ") or "Used"
    
        # Search for shoes
        # print("\nSearching eBay for sales data...")
        # df = search_shoes(sku, brand, model, size, condition)
    
    # if df is None or df.empty:
         #print("No results found")
       #  return

    df = search_shoes(sku) 
    if df.empty:
        print("No results found") 
    else:
        print(df)
        metrics = calculate_metrics(df)
        if metrics:
            print("\nSales Metrics:")
            for key, value in metrics.items():
                print(f"{key.capitalize()}: {value}")

if __name__ == "__main__":
    main()
