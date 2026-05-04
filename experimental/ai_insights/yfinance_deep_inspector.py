import yfinance as yf
import pandas as pd
import inspect
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def get_type_and_signature(obj, attr_name):
    """
    Safely inspects an attribute to determine its type and (if it's a method) its signature.
    """
    try:
        # Get the actual attribute from the object
        attr_value = getattr(obj, attr_name)
        
        # 1. Is it a Method / Function?
        if inspect.ismethod(attr_value) or inspect.isroutine(attr_value):
            try:
                sig = inspect.signature(attr_value)
                return "METHOD", f"{attr_name}{sig}"
            except ValueError:
                return "BUILT-IN METHOD", f"{attr_name}(...)"
                
        # 2. Is it a Pandas DataFrame?
        elif isinstance(attr_value, pd.DataFrame):
            cols = list(attr_value.columns)
            col_preview = str(cols[:4]).replace("]", ", ...]") if len(cols) > 4 else str(cols)
            return "DATAFRAME", f"{attr_name} -> Columns: {col_preview}"
            
        # 3. Is it a Pandas Series?
        elif isinstance(attr_value, pd.Series):
            return "SERIES", f"{attr_name} -> Index length: {len(attr_value)}"
            
        # 4. Is it a Dictionary?
        elif isinstance(attr_value, dict):
            keys = list(attr_value.keys())
            key_preview = str(keys[:4]).replace("]", ", ...]") if len(keys) > 4 else str(keys)
            return "DICTIONARY", f"{attr_name} -> Keys: {key_preview}"
            
        # 5. Is it a List?
        elif isinstance(attr_value, list):
            return "LIST", f"{attr_name} -> Length: {len(attr_value)}"
            
        # 6. Other Properties (String, Float, Boolean, Custom Objects)
        else:
            return f"PROPERTY [{type(attr_value).__name__.upper()}]", attr_name

    except Exception as e:
         return "ERROR", f"{attr_name} (Failed to inspect: {str(e)[:40]})"

def run_deep_introspection(ticker_symbol="AAPL"):
    print("=" * 90)
    print(f"🔬 YFINANCE DEEP INTROSPECTION SCRIPT: [{ticker_symbol}]")
    print("=" * 90)
    
    stock = yf.Ticker(ticker_symbol)
    
    # Use dir() to get all attributes, filter out private methods (starting with '_')
    all_attributes = sorted([attr for attr in dir(stock) if not attr.startswith('_')])
    
    # Categorize attributes to make the output readable
    categorized_results = {
        "METHODS (Functions you can call)": [],
        "DATAFRAMES & SERIES (Tabular Data)": [],
        "DICTIONARIES (Key-Value Data)": [],
        "PROPERTIES & OTHERS": [],
        "ERRORS": []
    }
    
    print("\nScanning library structure... Please wait, fetching live data types...\n")
    
    for attr in all_attributes:
        data_type, description = get_type_and_signature(stock, attr)
        
        if "METHOD" in data_type:
            categorized_results["METHODS (Functions you can call)"].append(description)
        elif "DATAFRAME" in data_type or "SERIES" in data_type:
            categorized_results["DATAFRAMES & SERIES (Tabular Data)"].append(description)
        elif "DICTIONARY" in data_type:
            categorized_results["DICTIONARIES (Key-Value Data)"].append(description)
        elif "ERROR" in data_type:
            categorized_results["ERRORS"].append(description)
        else:
            categorized_results["PROPERTIES & OTHERS"].append(f"{data_type.ljust(20)} | {description}")

    # --- PRINT THE RESULTS ---
    for category, items in categorized_results.items():
        if items:
            print(f"\n[{category}]")
            print("-" * 90)
            for item in items:
                print(f"  ➤ {item}")

    print("\n" + "=" * 90)
    print(f"✅ DEEP SCAN COMPLETE. Found {len(all_attributes)} public members in yf.Ticker.")
    print("=" * 90)

if __name__ == "__main__":
    # Test with a highly capitalized stock to populate all fields
    run_deep_introspection("MSFT")