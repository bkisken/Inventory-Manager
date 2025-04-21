import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
from PIL import Image, ImageTk
import requests
import threading
import cv2
from pyzbar.pyzbar import decode
import re
import time

# Get the absolute path of the parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)

# Import the StockX API
try:
    from stockxcaller import SneakerAPI
except ImportError:
    print("Warning: stockxcaller module not found. StockX functionality will be limited.")
    SneakerAPI = None

# Import our unified search module
try:
    from unified_search import UnifiedSneakerSearch
except ImportError:
    print("Warning: unified_search module not found. Please ensure it's in the correct directory.")
    UnifiedSneakerSearch = None

# Constants
INVENTORY_FILE = "inventory_data.json"
DEFAULT_SIZES = [
    "4", "4.5", "5", "5.5", "6", "6.5", "7", "7.5", "8", "8.5", 
    "9", "9.5", "10", "10.5", "11", "11.5", "12", "12.5", "13", "14", "15"
]

# Barcode API settings
BARCODE_API_KEY = "ln052jx0lgrqtbtbqpgpwqj2w4he7s"

class BarcodeAPI:
    def __init__(self):
        self.api_key = BARCODE_API_KEY
        self.base_url = "https://api.barcodelookup.com/v3/products"

    def search_barcode(self, barcode: str):
        try:
            url = f"{self.base_url}?barcode="
            querystring = url + barcode + "&formatted=y&key=" + self.api_key
            response = requests.request("GET", querystring)
            response.raise_for_status()
            
            data = response.json()
            return data.get('products', [])

        except requests.RequestException as e:
            print(f"Error searching for '{barcode}': {e}")
            return []


class InventoryManager:
    def __init__(self):
        self.unified_searcher = UnifiedSneakerSearch() if UnifiedSneakerSearch else None 
        self.inventories = self.load_inventory_data()
        self.api = SneakerAPI() if SneakerAPI else None
        self.barcode_api = BarcodeAPI()
        
    def load_inventory_data(self):
        """Load existing inventory data from file"""
        try:
            with open(INVENTORY_FILE, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
            
    def save_inventory_data(self):
        """Save inventory data to file"""
        with open(INVENTORY_FILE, 'w') as file:
            json.dump(self.inventories, file, indent=2)
            
    def create_inventory(self, inventory_name):
        """Create a new inventory"""
        if inventory_name not in self.inventories:
            self.inventories[inventory_name] = {}
            self.save_inventory_data()
            return True
        return False
        
    def extract_sku_patterns(self, product):
        """
        Try to find potential SKU patterns in the product data
        """
        potential_skus = []
        
        # Common SKU patterns for sneakers
        # Nike pattern: 2-3 letters followed by numbers and possible dash with more numbers (e.g., AJ1986-100)
        nike_pattern = r'[A-Z]{2,3}\d{4,6}(?:-\d{3})?'
        
        # Adidas pattern: 1-2 letters followed by numbers (e.g., FZ5456, GW2497)
        adidas_pattern = r'[A-Z]{1,2}\d{4,6}'
        
        # General alphanumeric pattern with possible dash (common in most shoe SKUs)
        general_pattern = r'[A-Z0-9]{5,12}(?:-\d{3})?'
        
        # Fields to search for SKUs
        fields_to_check = [
            product.get("mpn", ""),
            product.get("model", ""),
            product.get("title", ""),
            product.get("description", "")
        ]
        
        for field in fields_to_check:
            if not field:
                continue
                
            # Try Nike pattern
            nike_matches = re.findall(nike_pattern, field.upper())
            potential_skus.extend(nike_matches)
            
            # Try Adidas pattern
            adidas_matches = re.findall(adidas_pattern, field.upper())
            potential_skus.extend(adidas_matches)
            
            # Try general pattern if nothing found yet
            if not potential_skus:
                general_matches = re.findall(general_pattern, field.upper())
                potential_skus.extend(general_matches)
        
        # Remove duplicates and return
        return list(set(potential_skus))
        
    def extract_product_info(self, product_data):
        """
        Extract useful product information from barcode API response
        """
        if not product_data:
            return None
        
        product = product_data[0]  # Get the first product
        
        # Try to find potential SKUs
        potential_skus = self.extract_sku_patterns(product)
        
        # Get retail price
        retail_price = self.get_retail_price(product.get("stores", []))
        
        return {
            "title": product.get("title", ""),
            "brand": product.get("brand", ""),
            "mpn": product.get("mpn", ""),
            "barcode": product.get("barcode_number", ""),
            "category": product.get("category", ""),
            "color": product.get("color", ""),
            "size": product.get("size", ""),
            "potential_skus": potential_skus,
            "retail_price": retail_price,
            "description": product.get("description", "")
        }
        
    def get_retail_price(self, stores):
        """
        Get the average retail price from store listings
        """
        if not stores:
            return 0.0
        
        prices = []
        for store in stores:
            if store.get("country") == "US" and store.get("currency") == "USD":
                try:
                    price = float(store.get("price", "0"))
                    if price > 0:
                        prices.append(price)
                except ValueError:
                    continue
        
        return round(sum(prices) / len(prices), 2) if prices else 0.0
        
    def get_shoe_details(self, sku):
        """Fetch shoe details using the unified search"""
        if not self.unified_searcher:
            # Fallback to existing StockX-only implementation
            if not self.api:
                return {
                    "name": "Unknown",
                    "brand": "Unknown",
                    "retail_price": 0,
                    "avg_price": 0,
                    "sku": sku,
                    "stockx_price": 0,
                    "ebay_price": 0,
                    "goat_price": 0,
                    "high_price": 0,
                    "low_price": 0,
                    "total_sales": 0
                }
                
            try:
                # Use existing StockX implementation
                products = self.api.search_products(sku)
                if products and len(products) > 0:
                    product = products[0]
                    return {
                        "name": product.name,
                        "brand": product.brand,
                        "retail_price": product.retail_price,
                        "avg_price": product.avg_price,
                        "sku": sku,
                        "stockx_price": product.avg_price,
                        "ebay_price": 0,
                        "goat_price": 0,
                        "high_price": product.avg_price,
                        "low_price": product.avg_price,
                        "total_sales": 0
                    }
                else:
                    return {
                        "name": "Unknown",
                        "brand": "Unknown",
                        "retail_price": 0,
                        "avg_price": 0,
                        "sku": sku,
                        "stockx_price": 0,
                        "ebay_price": 0,
                        "goat_price": 0,
                        "high_price": 0,
                        "low_price": 0,
                        "total_sales": 0
                    }
            except Exception as e:
                print(f"Error fetching shoe details: {e}")
                return {
                    "name": "Unknown",
                    "brand": "Unknown",
                    "retail_price": 0,
                    "avg_price": 0,
                    "sku": sku,
                    "stockx_price": 0,
                    "ebay_price": 0,
                    "goat_price": 0,
                    "high_price": 0,
                    "low_price": 0,
                    "total_sales": 0
                }
            
        try:
            # Use the unified search to get combined data
            search_results = self.unified_searcher.search(sku)
            
            # Extract data from the aggregated results
            aggregated = search_results['aggregated']
            
            # Extract platform-specific prices
            stockx_price = search_results['stockx'].get('avg_price', 0) if search_results['stockx'] and search_results['stockx'].get('success', False) else 0
            
            ebay_price = 0
            if search_results['ebay'] and search_results['ebay'].get('success', False):
                ebay_price = search_results['ebay']['data'].get('average_price', 0)
            
            goat_price = 0
            if search_results['goat'] and search_results['goat'].get('success', False):
                goat_price = search_results['goat']['data'].get('lowestPrice', 0)
            
            return {
                "name": aggregated['name'] or "Unknown",
                "brand": aggregated['brand'] or "Unknown",
                "retail_price": aggregated['retail_price'] or 0,
                "avg_price": aggregated['avg_price'] or 0,
                "sku": sku,
                "stockx_price": stockx_price or 0,
                "ebay_price": ebay_price or 0,
                "goat_price": goat_price or 0,
                "high_price": aggregated['highest_price'] or 0,
                "low_price": aggregated['lowest_price'] or 0,
                "total_sales": aggregated['total_sales'] or 0
            }
        except Exception as e:
            print(f"Error fetching shoe details using unified search: {e}")
            # Fall back to existing StockX implementation
            return self.get_stockx_details(sku)
    
    def add_shoe(self, inventory_name, sku, size, quantity=1, condition="New", color="Unknown", manual_retail_price=None):
        """Add a shoe to an inventory"""
        if inventory_name not in self.inventories:
            return False
            
        # Get shoe details from API
        shoe_details = self.get_shoe_details(sku)
        
        # Override with manual retail price if provided
        if manual_retail_price is not None:
            shoe_details["retail_price"] = manual_retail_price
        
        # Ensure numeric values are never None
        if shoe_details["retail_price"] is None:
            shoe_details["retail_price"] = 0
        if shoe_details["avg_price"] is None:
            shoe_details["avg_price"] = 0
        
        # Create shoe entry if it doesn't exist
        if sku not in self.inventories[inventory_name]:
            self.inventories[inventory_name][sku] = {
                "name": shoe_details["name"],
                "brand": shoe_details["brand"],
                "retail_price": shoe_details["retail_price"],
                "avg_price": shoe_details["avg_price"],
                "stockx_price": shoe_details.get("stockx_price", 0),
                "ebay_price": shoe_details.get("ebay_price", 0),
                "goat_price": shoe_details.get("goat_price", 0),
                "high_price": shoe_details.get("high_price", 0),
                "low_price": shoe_details.get("low_price", 0),
                "total_sales": shoe_details.get("total_sales", 0),
                "sizes": {}
            }
                
        # Add or update size entry
        if size not in self.inventories[inventory_name][sku]["sizes"]:
            self.inventories[inventory_name][sku]["sizes"][size] = {
                "quantity": quantity,
                "condition": condition,
                "color": color
            }
        else:
            # Update existing size entry
            self.inventories[inventory_name][sku]["sizes"][size]["quantity"] += quantity
            self.inventories[inventory_name][sku]["sizes"][size]["condition"] = condition
            self.inventories[inventory_name][sku]["sizes"][size]["color"] = color
                
        self.save_inventory_data()
        return True
        
    def get_inventory_names(self):
        """Get a list of all inventory names"""
        return list(self.inventories.keys())
        
    def get_inventory(self, inventory_name):
        """Get all shoes in an inventory"""
        return self.inventories.get(inventory_name, {})
        
    def get_shoe(self, inventory_name, sku):
        """Get details for a specific shoe"""
        if inventory_name not in self.inventories:
            return None
        return self.inventories[inventory_name].get(sku, None)
        
    def remove_shoe(self, inventory_name, sku, size=None):
        """Remove a shoe from inventory"""
        if inventory_name not in self.inventories:
            return False
            
        if sku not in self.inventories[inventory_name]:
            return False
            
        if size:
            # Remove just the specific size
            if size in self.inventories[inventory_name][sku]["sizes"]:
                del self.inventories[inventory_name][sku]["sizes"][size]
                # If no sizes left, remove the entire shoe
                if not self.inventories[inventory_name][sku]["sizes"]:
                    del self.inventories[inventory_name][sku]
        else:
            # Remove the entire shoe
            del self.inventories[inventory_name][sku]
            
        self.save_inventory_data()
        return True
        
    def handle_scan(self, callback):
        """Handle barcode scan using camera and return the SKU and product info"""
        # Create a new window for the scanner
        scan_window = tk.Toplevel()
        scan_window.title("Barcode Scanner")
        scan_window.geometry("640x520")
        
        # Create frame for video
        video_frame = ttk.Frame(scan_window)
        video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create label for video display
        video_label = ttk.Label(video_frame)
        video_label.pack(padx=10, pady=10)
        
        # Create status label
        status_var = tk.StringVar(value="Scanning... (Press 'q' to quit without scanning)")
        status_label = ttk.Label(scan_window, textvariable=status_var)
        status_label.pack(padx=10, pady=5)
        
        # Create a canvas for video display
        canvas = tk.Canvas(video_frame, width=640, height=480)
        canvas.pack()
        
        # Initialize variables
        cap = None
        running = True
        last_barcode = ""
        last_scan_time = 0
        cooldown_period = 2  # Seconds between processing the same barcode
        
        def update_frame():
            nonlocal cap, running, last_barcode, last_scan_time
            
            if not running:
                return
                
            ret, frame = cap.read()
            if not ret:
                status_var.set("Error: Could not read from camera")
                return
                
            # Process the frame to find barcodes
            decoded_objects = decode(frame)
            
            current_time = time.time()
            
            for d in decoded_objects:
                barcode = d.data.decode()
                
                # Draw rectangle around barcode
                cv2.rectangle(frame, (d.rect.left, d.rect.top),
                            (d.rect.left + d.rect.width, d.rect.top + d.rect.height), (0, 255, 0), 3)
                cv2.putText(frame, barcode, (d.rect.left, d.rect.top + d.rect.height),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                
                # Only process if it's a new barcode or cooldown has passed
                if barcode != last_barcode or (current_time - last_scan_time) > cooldown_period:
                    last_barcode = barcode
                    last_scan_time = current_time
                    
                    status_var.set(f"Scanned Barcode: {barcode} - Looking up product...")
                    
                    # Process the barcode in a separate thread to keep UI responsive
                    threading.Thread(target=process_barcode, args=(barcode,)).start()
            
            # Convert frame to format compatible with tkinter
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Update canvas
            canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            canvas.image = imgtk
            
            # Schedule the next frame update
            if running:
                canvas.after(10, update_frame)
        
        def process_barcode(barcode):
            """Process the scanned barcode and lookup products"""
            # Get product info from Barcode API
            status_var.set(f"Looking up barcode {barcode}...")
            
            products = self.barcode_api.search_barcode(barcode)
            
            if products:
                product_info = self.extract_product_info(products)
                
                if product_info and product_info['potential_skus']:
                    status_var.set("Product found! Looking for matching SKU in StockX...")
                    
                    # Search potential SKUs in StockX
                    found_sku = None
                    stockx_info = None
                    
                    for sku in product_info['potential_skus']:
                        if self.api:
                            stockx_results = self.api.search_products(sku)
                            if stockx_results:
                                found_sku = sku
                                stockx_info = {
                                    "sku": sku,
                                    "name": stockx_results[0].name,
                                    "brand": stockx_results[0].brand,
                                    "retail_price": stockx_results[0].retail_price,
                                    "color": product_info['color']
                                }
                                break
                    
                    if found_sku:
                        status_var.set(f"Found match: {stockx_info['name']} (SKU: {found_sku})")
                        
                        # Stop scanning and close window
                        stop_scanning()
                        
                        # Call the callback with the SKU and product info
                        callback(found_sku, stockx_info)
                    else:
                        status_var.set("No matching SKU found in StockX. Please manually enter a SKU.")
                        stop_scanning()
                        manual_sku = simpledialog.askstring("Manual SKU Entry", "Enter the SKU:")
                        if manual_sku:
                            # Default product info if no StockX match was found
                            default_info = {
                                "sku": manual_sku,
                                "name": product_info['title'],
                                "brand": product_info['brand'],
                                "retail_price": product_info['retail_price'],
                                "color": product_info['color']
                            }
                            callback(manual_sku, default_info)
                else:
                    status_var.set("Product found but no potential SKUs identified. Please enter SKU manually.")
                    stop_scanning()
                    manual_sku = simpledialog.askstring("Manual SKU Entry", "Enter the SKU:")
                    if manual_sku:
                        # Default product info with minimal data
                        default_info = {
                            "sku": manual_sku,
                            "name": product_info['title'] if product_info else "Unknown",
                            "brand": product_info['brand'] if product_info else "Unknown",
                            "retail_price": product_info['retail_price'] if product_info else 0,
                            "color": product_info['color'] if product_info else "Unknown"
                        }
                        callback(manual_sku, default_info)
            else:
                status_var.set("No product information found for this barcode. Please enter SKU manually.")
                stop_scanning()
                manual_sku = simpledialog.askstring("Manual SKU Entry", "Enter the SKU:")
                if manual_sku:
                    # Minimal product info
                    default_info = {
                        "sku": manual_sku,
                        "name": "Unknown",
                        "brand": "Unknown",
                        "retail_price": 0,
                        "color": "Unknown"
                    }
                    callback(manual_sku, default_info)
        
        def stop_scanning():
            nonlocal running, cap
            running = False
            if cap is not None:
                cap.release()
            scan_window.destroy()
        
        def on_close():
            stop_scanning()
        
        def key_pressed(event):
            if event.char == 'q':
                stop_scanning()
                
        # Bind close event
        scan_window.protocol("WM_DELETE_WINDOW", on_close)
        scan_window.bind("<Key>", key_pressed)
        
        # Start camera in a separate thread to keep UI responsive
        def start_camera():
            nonlocal cap
            try:
                cap = cv2.VideoCapture(0)  # Use default camera
                if not cap.isOpened():
                    status_var.set("Error: Could not open camera")
                    return
                
                update_frame()
            except Exception as e:
                status_var.set(f"Error: {str(e)}")
        
        threading.Thread(target=start_camera).start()
        
        # Wait for window to be destroyed
        scan_window.wait_window()
        
        # If we got here without a callback being called, return None
        return None


class InventoryApp:
    def __init__(self, root, manager=None):
        self.root = root
        self.root.title("Shoe Inventory Manager")
        self.root.geometry("1000x600")
        self.root.minsize(800, 500)
        
        self.manager = manager or InventoryManager()
        self.current_inventory = tk.StringVar()
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create frames
        self.sidebar_frame = ttk.Frame(self.main_frame, width=250, relief="raised", borderwidth=1)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Setup sidebar
        self.setup_sidebar()
        
        # Setup content area
        self.setup_content()
        
        # Initialize dropdown with inventories
        self.update_inventory_dropdown()
        
    def setup_sidebar(self):
        """Setup the sidebar with inventory controls"""
        # Title
        title_label = ttk.Label(self.sidebar_frame, text="Inventory Control", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Inventory selection
        inventory_frame = ttk.LabelFrame(self.sidebar_frame, text="Select Inventory", padding=5)
        inventory_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.inventory_dropdown = ttk.Combobox(inventory_frame, textvariable=self.current_inventory)
        self.inventory_dropdown.pack(fill=tk.X, padx=5, pady=5)
        self.inventory_dropdown.bind("<<ComboboxSelected>>", self.on_inventory_selected)
        
        # Inventory actions
        action_frame = ttk.LabelFrame(self.sidebar_frame, text="Actions", padding=5)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        new_inventory_btn = ttk.Button(action_frame, text="Create New Inventory", command=self.create_new_inventory)
        new_inventory_btn.pack(fill=tk.X, padx=5, pady=5)
        
        add_shoe_btn = ttk.Button(action_frame, text="Add Shoe (Manual)", command=self.add_shoe_manual)
        add_shoe_btn.pack(fill=tk.X, padx=5, pady=5)
        
        scan_shoe_btn = ttk.Button(action_frame, text="Scan Shoe", command=self.scan_shoe)
        scan_shoe_btn.pack(fill=tk.X, padx=5, pady=5)
        
        remove_shoe_btn = ttk.Button(action_frame, text="Remove Selected Shoe", command=self.remove_selected_shoe)
        remove_shoe_btn.pack(fill=tk.X, padx=5, pady=5)

        # Add new button for updating prices
        update_prices_btn = ttk.Button(action_frame, text="Update Shoe Prices", command=self.update_all_shoe_prices)
        update_prices_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Stats area
        stats_frame = ttk.LabelFrame(self.sidebar_frame, text="Statistics", padding=5)
        stats_frame.pack(fill=tk.X, padx=5, pady=5, expand=True)
        
        self.total_items_label = ttk.Label(stats_frame, text="Total Items: 0")
        self.total_items_label.pack(anchor=tk.W, padx=5, pady=2)
        
        self.total_value_label = ttk.Label(stats_frame, text="Total Value: $0.00")
        self.total_value_label.pack(anchor=tk.W, padx=5, pady=2)
        
    def setup_content(self):
        """Setup the main content area with the inventory view"""
        # Create a frame for the treeview and scrollbar
        tree_frame = ttk.Frame(self.content_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create Treeview for inventory display with new columns for platform prices
        self.tree = ttk.Treeview(tree_frame, columns=("sku", "name", "brand", "retail", "avg", "stockx", "ebay", "goat", "high", "low", "sales", "quantity"))
        
        # Configure scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for tree and scrollbars
        self.tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")
        hsb.grid(column=0, row=1, sticky="ew")
        
        # Configure the grid weights
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Configure column headings
        self.tree.heading("#0", text="ID")
        self.tree.heading("sku", text="SKU")
        self.tree.heading("name", text="Name")
        self.tree.heading("brand", text="Brand")
        self.tree.heading("retail", text="Retail")
        self.tree.heading("avg", text="Avg")
        self.tree.heading("stockx", text="StockX")
        self.tree.heading("ebay", text="eBay")
        self.tree.heading("goat", text="GOAT")
        self.tree.heading("high", text="High")
        self.tree.heading("low", text="Low")
        self.tree.heading("sales", text="Sales")
        self.tree.heading("quantity", text="Qty")

        # Configure column widths
        self.tree.column("#0", width=40, stretch=False)
        self.tree.column("sku", width=80, stretch=False)
        self.tree.column("name", width=200)
        self.tree.column("brand", width=80)
        self.tree.column("retail", width=60, anchor=tk.E)
        self.tree.column("avg", width=60, anchor=tk.E)
        self.tree.column("stockx", width=60, anchor=tk.E)
        self.tree.column("ebay", width=60, anchor=tk.E)
        self.tree.column("goat", width=60, anchor=tk.E)
        self.tree.column("high", width=60, anchor=tk.E)
        self.tree.column("low", width=60, anchor=tk.E)
        self.tree.column("sales", width=50, anchor=tk.CENTER)
        self.tree.column("quantity", width=40, anchor=tk.CENTER)
        
        # Create a details frame
        details_frame = ttk.LabelFrame(self.content_frame, text="Selected Shoe Details", padding=5)
        details_frame.pack(fill=tk.X, pady=5)
        
        # Configure the details view
        details_grid = ttk.Frame(details_frame)
        details_grid.pack(fill=tk.X, padx=5, pady=5)
        
        # Details labels
        ttk.Label(details_grid, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.detail_name = ttk.Label(details_grid, text="")
        self.detail_name.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(details_grid, text="SKU:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.detail_sku = ttk.Label(details_grid, text="")
        self.detail_sku.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(details_grid, text="Brand:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.detail_brand = ttk.Label(details_grid, text="")
        self.detail_brand.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        # First row of pricing info
        ttk.Label(details_grid, text="Retail:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.detail_retail = ttk.Label(details_grid, text="")
        self.detail_retail.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

        ttk.Label(details_grid, text="Avg Price:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.detail_avg_price = ttk.Label(details_grid, text="")
        self.detail_avg_price.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)

        ttk.Label(details_grid, text="Total Sales:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.detail_sales = ttk.Label(details_grid, text="")
        self.detail_sales.grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)

        # Second row of pricing info (platform-specific)
        ttk.Label(details_grid, text="StockX Price:").grid(row=0, column=4, sticky=tk.W, padx=5, pady=2)
        self.detail_stockx = ttk.Label(details_grid, text="")
        self.detail_stockx.grid(row=0, column=5, sticky=tk.W, padx=5, pady=2)

        ttk.Label(details_grid, text="eBay Price:").grid(row=1, column=4, sticky=tk.W, padx=5, pady=2)
        self.detail_ebay = ttk.Label(details_grid, text="")
        self.detail_ebay.grid(row=1, column=5, sticky=tk.W, padx=5, pady=2)

        ttk.Label(details_grid, text="GOAT Price:").grid(row=2, column=4, sticky=tk.W, padx=5, pady=2)
        self.detail_goat = ttk.Label(details_grid, text="")
        self.detail_goat.grid(row=2, column=5, sticky=tk.W, padx=5, pady=2)
        
        # Sizes frame
        self.sizes_frame = ttk.LabelFrame(details_frame, text="Sizes")
        self.sizes_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
    def update_inventory_dropdown(self):
        """Update the inventory dropdown with available inventories"""
        inventories = self.manager.get_inventory_names()
        self.inventory_dropdown["values"] = inventories
        
        if inventories:
            self.current_inventory.set(inventories[0])
            self.on_inventory_selected(None)  # Load the first inventory
            
    def on_inventory_selected(self, event):
        """Handle inventory selection from dropdown"""
        inventory_name = self.current_inventory.get()
        if inventory_name:
            self.load_inventory(inventory_name)
            
    def load_inventory(self, inventory_name):
        """Load and display the selected inventory"""
        inventory = self.manager.get_inventory(inventory_name)
        
        # Clear the tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Clear details
        self.clear_details()
        
        # Insert inventory items into the tree
        total_items = 0
        total_value = 0
        
        for i, (sku, details) in enumerate(inventory.items()):
            name = details.get("name", "Unknown")
            brand = details.get("brand", "Unknown")
            
            # Fix: Ensure retail_price and avg_price are never None
            retail_price = details.get("retail_price", 0)
            if retail_price is None:
                retail_price = 0
                
            avg_price = details.get("avg_price", 0)
            if avg_price is None:
                avg_price = 0
            
            # Calculate total quantity across all sizes
            sizes = details.get("sizes", {})
            quantity = sum(size_info.get("quantity", 0) for size_info in sizes.values())
            
            # Add to totals
            total_items += quantity
            total_value += quantity * avg_price  # This should now be safe
            
            # Insert into tree
            self.tree.insert("", tk.END, text=str(i+1), values=(
                sku, name, brand, 
                f"${retail_price:.2f}" if retail_price else "N/A",
                f"${avg_price:.2f}" if avg_price else "N/A",
                f"${details.get('stockx_price', 0):.2f}" if details.get('stockx_price') else "N/A",
                f"${details.get('ebay_price', 0):.2f}" if details.get('ebay_price') else "N/A",
                f"${details.get('goat_price', 0):.2f}" if details.get('goat_price') else "N/A",
                f"${details.get('high_price', 0):.2f}" if details.get('high_price') else "N/A",
                f"${details.get('low_price', 0):.2f}" if details.get('low_price') else "N/A",
                details.get('total_sales', 0),
                quantity
            ), iid=sku)
            
        # Update statistics
        self.total_items_label.config(text=f"Total Items: {total_items}")
        self.total_value_label.config(text=f"Total Value: ${total_value:.2f}")
        
    def on_tree_select(self, event):
        """Handle tree item selection"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        sku = selected_items[0]  # Get the SKU (used as the iid)
        inventory_name = self.current_inventory.get()
        
        if not inventory_name:
            return
            
        shoe = self.manager.get_shoe(inventory_name, sku)
        if not shoe:
            return
            
        # Update details view
        self.detail_name.config(text=shoe.get("name", "Unknown"))
        self.detail_sku.config(text=sku)
        self.detail_brand.config(text=shoe.get("brand", "Unknown"))

        # Update price details
        retail_price = shoe.get("retail_price", 0) or 0
        avg_price = shoe.get("avg_price", 0) or 0
        stockx_price = shoe.get("stockx_price", 0) or 0
        ebay_price = shoe.get("ebay_price", 0) or 0
        goat_price = shoe.get("goat_price", 0) or 0
        total_sales = shoe.get("total_sales", 0) or 0

        self.detail_retail.config(text=f"${retail_price:.2f}")
        self.detail_avg_price.config(text=f"${avg_price:.2f}")
        self.detail_stockx.config(text=f"${stockx_price:.2f}")
        self.detail_ebay.config(text=f"${ebay_price:.2f}")
        self.detail_goat.config(text=f"${goat_price:.2f}")
        self.detail_sales.config(text=f"{total_sales}")
        
        # Clear existing size widgets
        for widget in self.sizes_frame.winfo_children():
            widget.destroy()
            
        # Add size information
        sizes = shoe.get("sizes", {})
        
        # Create a size grid with 5 columns
        row, col = 0, 0
        for size, size_info in sizes.items():
            qty = size_info.get("quantity", 0)
            condition = size_info.get("condition", "New")
            color = size_info.get("color", "Unknown")
            
            size_frame = ttk.Frame(self.sizes_frame)
            size_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nw")
            
            ttk.Label(size_frame, text=f"Size: {size}").grid(row=0, column=0, sticky=tk.W)
            ttk.Label(size_frame, text=f"Qty: {qty}").grid(row=1, column=0, sticky=tk.W)
            ttk.Label(size_frame, text=f"Cond: {condition}").grid(row=2, column=0, sticky=tk.W)
            ttk.Label(size_frame, text=f"Color: {color}").grid(row=3, column=0, sticky=tk.W)
            
            col += 1
            if col >= 5:  # 5 columns per row
                col = 0
                row += 1
                
    def clear_details(self):
        """Clear the details panel"""
        self.detail_name.config(text="")
        self.detail_sku.config(text="")
        self.detail_brand.config(text="")
        self.detail_retail.config(text="")
        self.detail_avg_price.config(text="")
        
        for widget in self.sizes_frame.winfo_children():
            widget.destroy()
            
    def create_new_inventory(self):
        """Create a new inventory"""
        inventory_name = simpledialog.askstring("New Inventory", "Enter inventory name:")
        if inventory_name:
            if self.manager.create_inventory(inventory_name):
                messagebox.showinfo("Success", f"Inventory '{inventory_name}' created.")
                self.update_inventory_dropdown()
                self.current_inventory.set(inventory_name)
                self.on_inventory_selected(None)
            else:
                messagebox.showerror("Error", f"Inventory '{inventory_name}' already exists.")
                
    def add_shoe_manual(self):
        """Add a shoe manually"""
        inventory_name = self.current_inventory.get()
        if not inventory_name:
            messagebox.showerror("Error", "Please select an inventory first.")
            return
            
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Shoe")
        dialog.geometry("400x450")  # Made taller to accommodate the new field
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Dialog content
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="SKU:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        sku_var = tk.StringVar()
        sku_entry = ttk.Entry(frame, textvariable=sku_var)
        sku_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(frame, text="Size:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        size_var = tk.StringVar()
        size_combobox = ttk.Combobox(frame, textvariable=size_var, values=DEFAULT_SIZES)
        size_combobox.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(frame, text="Quantity:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        qty_var = tk.IntVar(value=1)
        qty_spinbox = ttk.Spinbox(frame, from_=1, to=100, textvariable=qty_var)
        qty_spinbox.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(frame, text="Condition:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        condition_var = tk.StringVar(value="New")
        condition_combobox = ttk.Combobox(frame, textvariable=condition_var, 
                                        values=["New", "Used", "Worn"])
        condition_combobox.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(frame, text="Color:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        color_var = tk.StringVar()
        color_entry = ttk.Entry(frame, textvariable=color_var)
        color_entry.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Add retail price field
        ttk.Label(frame, text="Retail Price ($):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        retail_var = tk.DoubleVar(value=0.00)
        retail_entry = ttk.Entry(frame, textvariable=retail_var)
        retail_entry.grid(row=5, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Status label
        status_var = tk.StringVar()
        status_label = ttk.Label(frame, textvariable=status_var, foreground="blue")
        status_label.grid(row=6, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        
        # Fetch button
        def fetch_details():
            sku = sku_var.get().strip()
            if not sku:
                status_var.set("Please enter a SKU")
                return
                
            status_var.set("Fetching details...")
            
            def fetch_thread():
                details = self.manager.get_shoe_details(sku)
                
                # Update status
                dialog.after(0, lambda: status_var.set(
                    f"Found: {details['name']}" if details['name'] != 'Unknown' else "No details found"
                ))
                
                # Set retail price if available
                if details['retail_price']:
                    dialog.after(0, lambda: retail_var.set(details['retail_price']))
            
            # Start fetch in a separate thread
            threading.Thread(target=fetch_thread).start()
                
        fetch_btn = ttk.Button(frame, text="Fetch Details", command=fetch_details)
        fetch_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Button frame
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=7, column=0, columnspan=3, pady=10)
        
        # Add button
        def add_shoe():
            sku = sku_var.get().strip()
            size = size_var.get().strip()
            qty = qty_var.get()
            condition = condition_var.get()
            color = color_var.get().strip()
            retail_price = retail_var.get()
            
            if not sku or not size:
                status_var.set("SKU and Size are required")
                return
                
            if self.manager.add_shoe(inventory_name, sku, size, qty, condition, color, retail_price):
                dialog.destroy()
                self.load_inventory(inventory_name)
                messagebox.showinfo("Success", f"Added {qty} x Size {size} of SKU {sku}")
            else:
                status_var.set("Failed to add shoe")
                    
        add_btn = ttk.Button(btn_frame, text="Add Shoe", command=add_shoe)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Configure resizing
        frame.columnconfigure(1, weight=1)
        
        # Focus and wait
        sku_entry.focus_set()
        dialog.wait_window()
        
    def scan_shoe(self):
        """Handle shoe scan"""
        inventory_name = self.current_inventory.get()
        if not inventory_name:
            messagebox.showerror("Error", "Please select an inventory first.")
            return
            
        # Use the manager to handle the scan
        self.manager.handle_scan(lambda sku, product_info: self.process_scanned_sku(sku, inventory_name, product_info))
        
    def process_scanned_sku(self, sku, inventory_name, product_info=None):
        """Process a scanned SKU with product information"""
        if not sku:
            return
            
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Scanned SKU: {sku}")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Dialog content
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        status_var = tk.StringVar(value="Product found! Complete the form to add to inventory." if product_info else "Fetching product details...")
        status_label = ttk.Label(frame, textvariable=status_var)
        status_label.pack(fill=tk.X, pady=5)
        
        # Product details
        details_frame = ttk.LabelFrame(frame, text="Product Details")
        details_frame.pack(fill=tk.X, pady=5)
        
        # Details variables
        name_var = tk.StringVar(value=product_info["name"] if product_info else "Loading...")
        brand_var = tk.StringVar(value=product_info["brand"] if product_info else "Loading...")
        retail_var = tk.StringVar(value=f"${product_info['retail_price']:.2f}" if product_info and product_info['retail_price'] else "N/A")
        
        # Details grid
        details_grid = ttk.Frame(details_frame)
        details_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(details_grid, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(details_grid, textvariable=name_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(details_grid, text="Brand:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(details_grid, textvariable=brand_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(details_grid, text="Retail:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(details_grid, textvariable=retail_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Size and quantity
        input_frame = ttk.LabelFrame(frame, text="Add to Inventory")
        input_frame.pack(fill=tk.X, pady=5)
        
        input_grid = ttk.Frame(input_frame)
        input_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(input_grid, text="Size:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        size_var = tk.StringVar()
        # Set default size if available in product info
        if product_info and product_info.get("size"):
            size_var.set(product_info["size"])
            
        size_combobox = ttk.Combobox(input_grid, textvariable=size_var, values=DEFAULT_SIZES)
        size_combobox.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(input_grid, text="Quantity:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        qty_var = tk.IntVar(value=1)
        qty_spinbox = ttk.Spinbox(input_grid, from_=1, to=100, textvariable=qty_var)
        qty_spinbox.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(input_grid, text="Condition:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        condition_var = tk.StringVar(value="New")
        condition_combobox = ttk.Combobox(input_grid, textvariable=condition_var, 
                                        values=["New", "Used", "Worn"])
        condition_combobox.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(input_grid, text="Color:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        color_var = tk.StringVar(value=product_info.get("color", "") if product_info else "")
        color_entry = ttk.Entry(input_grid, textvariable=color_var)
        color_entry.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Add manual retail price field
        ttk.Label(input_grid, text="Retail Price ($):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        manual_retail_var = tk.DoubleVar(value=product_info.get("retail_price", 0.0) if product_info else 0.0)
        retail_entry = ttk.Entry(input_grid, textvariable=manual_retail_var)
        retail_entry.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        # Add button
        def add_scanned_shoe():
            size = size_var.get().strip()
            qty = qty_var.get()
            condition = condition_var.get()
            color = color_var.get().strip()
            retail_price = manual_retail_var.get()
            
            if not size:
                status_var.set("Size is required")
                return
                
            if self.manager.add_shoe(inventory_name, sku, size, qty, condition, color, retail_price):
                dialog.destroy()
                self.load_inventory(inventory_name)
                messagebox.showinfo("Success", f"Added {qty} x Size {size} of SKU {sku}")
            else:
                status_var.set("Failed to add shoe")
                
        # If no product_info was provided, fetch details from StockX
        if not product_info:
            def fetch_details_thread():
                details = self.manager.get_shoe_details(sku)
                
                # Update UI on the main thread
                dialog.after(0, lambda: update_ui(details))
                
            def update_ui(details):
                # Update status and product details
                if details["name"] != "Unknown":
                    status_var.set("Product found! Complete the form to add to inventory.")
                    name_var.set(details["name"])
                    brand_var.set(details["brand"])
                    retail_var.set(f"${details['retail_price']:.2f}" if details["retail_price"] else "N/A")
                    
                    # Set retail price field if available
                    if details["retail_price"]:
                        manual_retail_var.set(details["retail_price"])
                else:
                    status_var.set("Product not found. You can still add it manually.")
                    name_var.set("Unknown")
                    brand_var.set("Unknown")
                    retail_var.set("N/A")
            
            # Start the fetch thread
            threading.Thread(target=fetch_details_thread).start()
        
        add_btn = ttk.Button(btn_frame, text="Add to Inventory", command=add_scanned_shoe)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Configure resizing
        input_grid.columnconfigure(1, weight=1)
        
        # Focus and wait
        size_combobox.focus_set()
        dialog.wait_window()
        
    def remove_selected_shoe(self):
        """Remove the selected shoe from inventory"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select a shoe to remove.")
            return
            
        sku = selected_items[0]  # Get the SKU (used as the iid)
        inventory_name = self.current_inventory.get()
        
        if not inventory_name:
            return
            
        # Ask for confirmation
        result = messagebox.askyesno("Confirm Removal", 
                                    f"Are you sure you want to remove SKU {sku} from inventory?")
        if result:
            # Ask if they want to remove a specific size or the entire shoe
            remove_options = ["Remove specific size", "Remove entire shoe"]
            choice = simpledialog.askinteger("Remove Options", 
                                            "Select option:\n1. Remove specific size\n2. Remove entire shoe",
                                            minvalue=1, maxvalue=2)
            
            if choice == 1:  # Remove specific size
                shoe = self.manager.get_shoe(inventory_name, sku)
                if not shoe:
                    return
                    
                sizes = list(shoe.get("sizes", {}).keys())
                if not sizes:
                    messagebox.showinfo("Info", "No sizes found for this shoe.")
                    return
                    
                size_dialog = tk.Toplevel(self.root)
                size_dialog.title("Select Size to Remove")
                size_dialog.geometry("300x200")
                size_dialog.transient(self.root)
                size_dialog.grab_set()
                
                frame = ttk.Frame(size_dialog, padding=10)
                frame.pack(fill=tk.BOTH, expand=True)
                
                ttk.Label(frame, text="Select size to remove:").pack(pady=5)
                
                size_var = tk.StringVar()
                size_listbox = tk.Listbox(frame)
                size_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
                
                for size in sizes:
                    size_listbox.insert(tk.END, size)
                    
                def remove_size():
                    selected = size_listbox.curselection()
                    if not selected:
                        return
                        
                    size = size_listbox.get(selected[0])
                    if self.manager.remove_shoe(inventory_name, sku, size):
                        self.load_inventory(inventory_name)
                        messagebox.showinfo("Success", f"Removed size {size} of SKU {sku}")
                    else:
                        messagebox.showerror("Error", "Failed to remove size")
                    size_dialog.destroy()
                    
                btn_frame = ttk.Frame(frame)
                btn_frame.pack(fill=tk.X, pady=5)
                
                ttk.Button(btn_frame, text="Remove", command=remove_size).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="Cancel", command=size_dialog.destroy).pack(side=tk.LEFT, padx=5)
                
                size_dialog.wait_window()
                
            elif choice == 2:  # Remove entire shoe
                if self.manager.remove_shoe(inventory_name, sku):
                    self.load_inventory(inventory_name)
                    messagebox.showinfo("Success", f"Removed SKU {sku} from inventory")
                else:
                    messagebox.showerror("Error", "Failed to remove shoe")
    
    def update_all_shoe_prices(self):
        """Update prices for all shoes in the current inventory"""
        inventory_name = self.current_inventory.get()
        
        if not inventory_name:
            messagebox.showerror("Error", "Please select an inventory first.")
            return
        
        inventory = self.manager.get_inventory(inventory_name)
        if not inventory:
            messagebox.showinfo("Info", "Inventory is empty.")
            return
        
        # Count total items
        total_items = len(inventory)
        if total_items == 0:
            messagebox.showinfo("Info", "No shoes in inventory to update.")
            return
        
        # Show status dialog
        status_dialog = tk.Toplevel(self.root)
        status_dialog.title("Updating All Prices")
        status_dialog.geometry("400x200")
        status_dialog.transient(self.root)
        status_dialog.grab_set()
        
        # Status content
        frame = ttk.Frame(status_dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        status_label = ttk.Label(frame, text=f"Updating prices for {total_items} shoes...")
        status_label.pack(pady=10)
        
        # Progress information
        progress_text = ttk.Label(frame, text="Processing item 0 of {}".format(total_items))
        progress_text.pack(pady=5)
        
        # Current item being processed
        current_item_label = ttk.Label(frame, text="")
        current_item_label.pack(pady=5)
        
        # Progress bar
        progress = ttk.Progressbar(frame, orient="horizontal", length=300, mode="determinate", maximum=total_items)
        progress.pack(fill=tk.X, pady=10)
        
        # Cancel button
        cancel_var = tk.BooleanVar(value=False)
        
        def cancel_update():
            cancel_var.set(True)
            status_label.config(text="Cancelling...")
        
        cancel_btn = ttk.Button(frame, text="Cancel", command=cancel_update)
        cancel_btn.pack(pady=5)
        
        # Function to update prices in a separate thread
        def update_thread():
            updated_count = 0
            skipped_count = 0
            error_count = 0
            
            try:
                # Process each shoe
                for i, (sku, shoe) in enumerate(inventory.items()):
                    # Check if cancel was requested
                    if cancel_var.get():
                        status_dialog.after(0, lambda: status_label.config(
                            text=f"Cancelled. Updated {updated_count} of {total_items} shoes."
                        ))
                        break
                    
                    # Update progress
                    status_dialog.after(0, lambda i=i, sku=sku: [
                        progress.config(value=i),
                        progress_text.config(text=f"Processing item {i+1} of {total_items}"),
                        current_item_label.config(text=f"Current: {sku}")
                    ])
                    
                    try:
                        # Get fresh details from all platforms
                        details = self.manager.get_shoe_details(sku)
                        
                        # Skip if no updated details found
                        if details["name"] == "Unknown" and details["brand"] == "Unknown":
                            skipped_count += 1
                            continue
                        
                        # Update the shoe in the inventory
                        shoe["avg_price"] = details["avg_price"]
                        shoe["stockx_price"] = details["stockx_price"]
                        shoe["ebay_price"] = details["ebay_price"]
                        shoe["goat_price"] = details["goat_price"]
                        shoe["high_price"] = details["high_price"]
                        shoe["low_price"] = details["low_price"]
                        shoe["total_sales"] = details["total_sales"]
                        
                        updated_count += 1
                        
                        # Save the inventory data periodically (every 5 items)
                        if updated_count % 5 == 0:
                            self.manager.save_inventory_data()
                        
                    except Exception as e:
                        print(f"Error updating {sku}: {str(e)}")
                        error_count += 1
                
                # Final save
                self.manager.save_inventory_data()
                
                # Update UI and close
                if not cancel_var.get():
                    status_dialog.after(0, lambda: [
                        status_label.config(text=f"Complete! Updated {updated_count} shoes."),
                        progress.config(value=total_items),
                        cancel_btn.config(text="Close")
                    ])
                    status_dialog.after(2000, lambda: [
                        status_dialog.destroy(), 
                        self.load_inventory(inventory_name),
                        messagebox.showinfo("Update Complete", 
                                            f"Updated: {updated_count}\nSkipped: {skipped_count}\nErrors: {error_count}")
                    ])
                else:
                    # Just enable the close button if cancelled
                    status_dialog.after(0, lambda: cancel_btn.config(text="Close"))
                    
            except Exception as e:
                status_dialog.after(0, lambda e=e: [
                    status_label.config(text=f"Error: {str(e)}"),
                    cancel_btn.config(text="Close")
                ])
        
        # Start update thread
        threading.Thread(target=update_thread).start()


def main():
    # Replace with your actual API key
    stockx_api_key = "YOUR_STOCKX_API_KEY"
    
    root = tk.Tk()
    manager = InventoryManager()
    app = InventoryApp(root, manager)
    root.mainloop()


if __name__ == "__main__":
    main()