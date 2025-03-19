import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
from PIL import Image, ImageTk
import requests
import threading

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

# Constants
INVENTORY_FILE = "inventory_data.json"
DEFAULT_SIZES = [
    "4", "4.5", "5", "5.5", "6", "6.5", "7", "7.5", "8", "8.5", 
    "9", "9.5", "10", "10.5", "11", "11.5", "12", "12.5", "13", "14", "15"
]

class InventoryManager:
    def __init__(self):
        self.inventories = self.load_inventory_data()
        self.api = SneakerAPI() if SneakerAPI else None
        
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
        
    def get_shoe_details(self, sku):
        """Fetch shoe details from StockX API"""
        if not self.api:
            return {
                "name": "Unknown",
                "brand": "Unknown",
                "retail_price": 0,
                "avg_price": 0,
                "sku": sku
            }
            
        try:
            products = self.api.search_products(sku)
            if products and len(products) > 0:
                product = products[0]
                return {
                    "name": product.name,
                    "brand": product.brand,
                    "retail_price": product.retail_price,
                    "avg_price": product.avg_price,
                    "sku": sku
                }
            else:
                return {
                    "name": "Unknown",
                    "brand": "Unknown",
                    "retail_price": 0,
                    "avg_price": 0,
                    "sku": sku
                }
        except Exception as e:
            print(f"Error fetching shoe details: {e}")
            return {
                "name": "Unknown",
                "brand": "Unknown",
                "retail_price": 0,
                "avg_price": 0,
                "sku": sku
            }
    
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
        """Handle barcode scan and return the SKU"""
        # This is a placeholder. In a real implementation, you would:
        # 1. Activate a barcode scanner
        # 2. Process the scan to extract the SKU
        # 3. Return the SKU or call the callback with the SKU
        
        # For testing, we'll just simulate a scan with a dialog box
        sku = simpledialog.askstring("Scan Barcode", "Enter or scan the SKU:")
        if sku and callback:
            callback(sku)
        return sku


class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Shoe Inventory Manager")
        self.root.geometry("1000x600")
        self.root.minsize(800, 500)
        
        self.manager = InventoryManager()
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
        
        # Create Treeview for inventory display
        self.tree = ttk.Treeview(tree_frame, columns=("sku", "name", "brand", "retail", "resell", "quantity"))
        
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
        self.tree.heading("resell", text="Resell")
        self.tree.heading("quantity", text="Qty")
        
        # Configure column widths
        self.tree.column("#0", width=50, stretch=False)
        self.tree.column("sku", width=100, stretch=False)
        self.tree.column("name", width=250)
        self.tree.column("brand", width=100)
        self.tree.column("retail", width=80, anchor=tk.E)
        self.tree.column("resell", width=80, anchor=tk.E)
        self.tree.column("quantity", width=50, anchor=tk.CENTER)
        
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
        
        ttk.Label(details_grid, text="Retail:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.detail_retail = ttk.Label(details_grid, text="")
        self.detail_retail.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(details_grid, text="Avg Price:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.detail_avg_price = ttk.Label(details_grid, text="")
        self.detail_avg_price.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
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
        self.detail_retail.config(text=f"${shoe.get('retail_price', 0):.2f}")
        self.detail_avg_price.config(text=f"${shoe.get('avg_price', 0):.2f}")
        
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
        self.manager.handle_scan(lambda sku: self.process_scanned_sku(sku, inventory_name))
        
    def process_scanned_sku(self, sku, inventory_name):
        """Process a scanned SKU"""
        if not sku:
            return
            
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Scanned SKU: {sku}")
        dialog.geometry("400x400")  # Made taller for the new field
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Dialog content
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        status_var = tk.StringVar(value="Fetching product details...")
        status_label = ttk.Label(frame, textvariable=status_var)
        status_label.pack(fill=tk.X, pady=5)
        
        # Product details
        details_frame = ttk.LabelFrame(frame, text="Product Details")
        details_frame.pack(fill=tk.X, pady=5)
        
        # Details variables
        name_var = tk.StringVar(value="Loading...")
        brand_var = tk.StringVar(value="Loading...")
        retail_var = tk.StringVar(value="Loading...")
        resell_var = tk.StringVar(value="Loading...")
        
        # Details grid
        details_grid = ttk.Frame(details_frame)
        details_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(details_grid, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(details_grid, textvariable=name_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(details_grid, text="Brand:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(details_grid, textvariable=brand_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(details_grid, text="Retail:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(details_grid, textvariable=retail_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(details_grid, text="Avg Price:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(details_grid, textvariable=resell_var).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Size and quantity
        input_frame = ttk.LabelFrame(frame, text="Add to Inventory")
        input_frame.pack(fill=tk.X, pady=5)
        
        input_grid = ttk.Frame(input_frame)
        input_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(input_grid, text="Size:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        size_var = tk.StringVar()
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
        color_var = tk.StringVar()
        color_entry = ttk.Entry(input_grid, textvariable=color_var)
        color_entry.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Add manual retail price field
        ttk.Label(input_grid, text="Retail Price ($):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        manual_retail_var = tk.DoubleVar(value=0.0)
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
                    
        # Fetch details in a separate thread
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
                resell_var.set(f"${details['avg_price']:.2f}" if details["avg_price"] else "N/A")
                
                # Set retail price field if available
                if details["retail_price"]:
                    manual_retail_var.set(details["retail_price"])
            else:
                status_var.set("Product not found. You can still add it manually.")
                name_var.set("Unknown")
                brand_var.set("Unknown")
                retail_var.set("N/A")
                resell_var.set("N/A")
                    
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


def main():
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()