#!/usr/bin/env python3
"""
Manufacturing Data Loader
Loads CSV data into PostgreSQL database for manufacturing schedule system.
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
import chardet

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManufacturingDataLoader:
    def __init__(self):
        self.conn = None
        self.cursor = None
        
    def detect_encoding(self, filepath):
        """Detect file encoding to handle different character sets."""
        with open(filepath, 'rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            return result['encoding']
    
    def read_csv_safe(self, filepath, **kwargs):
        """Safely read CSV with encoding detection."""
        try:
            # First try UTF-8
            return pd.read_csv(filepath, encoding='utf-8', **kwargs)
        except UnicodeDecodeError:
            # Detect encoding and try again
            encoding = self.detect_encoding(filepath)
            logger.info(f"Detected encoding for {filepath}: {encoding}")
            return pd.read_csv(filepath, encoding=encoding, **kwargs)
        
    def connect_to_db(self):
        """Connect to PostgreSQL database using environment variables."""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL not found in environment variables")
            
            self.conn = psycopg2.connect(database_url)
            self.cursor = self.conn.cursor()
            logger.info("Connected to database successfully")
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def drop_tables(self):
        """Drop all existing tables to recreate with correct schema."""
        try:
            drop_sql = [
                "DROP TABLE IF EXISTS product_ingredients CASCADE;",
                "DROP TABLE IF EXISTS products CASCADE;",
                "DROP TABLE IF EXISTS sales_history CASCADE;",
                "DROP TABLE IF EXISTS ingredient_lead_times CASCADE;",
                "DROP TABLE IF EXISTS stock_inventory CASCADE;"
            ]
            
            for sql in drop_sql:
                self.cursor.execute(sql)
            
            self.conn.commit()
            logger.info("All tables dropped successfully")
            
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            self.conn.rollback()
            raise
    
    def create_tables(self):
        """Create all necessary database tables."""
        
        tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS stock_inventory (
                id SERIAL PRIMARY KEY,
                product_code VARCHAR(100) UNIQUE NOT NULL,
                product_description TEXT,
                product_group VARCHAR(100),
                base_pack DECIMAL(15,4),
                allocated DECIMAL(15,4),
                on_hand DECIMAL(15,4),
                base_unit VARCHAR(20),
                snapshot_date DATE DEFAULT CURRENT_DATE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sales_history (
                id SERIAL PRIMARY KEY,
                shop VARCHAR(100),
                region VARCHAR(100),
                product VARCHAR(100),
                sale_month DATE,
                quantity INTEGER
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(50) UNIQUE NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS product_ingredients (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id),
                component TEXT,
                parent_component TEXT,
                intermediate_component TEXT,
                quantity DECIMAL(15,4),
                wastage DECIMAL(15,4),
                unit VARCHAR(20),
                unit_cost DECIMAL(12,4),
                total_cost DECIMAL(12,2)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS ingredient_lead_times (
                id SERIAL PRIMARY KEY,
                product_code VARCHAR(100),
                product_description TEXT,
                product_group VARCHAR(100),
                minimum_order_quantity INTEGER,
                lead_time_days INTEGER,
                base_unit VARCHAR(20)
            );
            """
        ]
        
        try:
            for sql in tables_sql:
                self.cursor.execute(sql)
            
            # Create indexes
            indexes_sql = [
                "CREATE INDEX IF NOT EXISTS idx_stock_product_code ON stock_inventory(product_code);",
                "CREATE INDEX IF NOT EXISTS idx_sales_shop_region ON sales_history(shop, region);",
                "CREATE INDEX IF NOT EXISTS idx_sales_month ON sales_history(sale_month);",
                "CREATE INDEX IF NOT EXISTS idx_ingredients_product ON product_ingredients(product_id);",
                "CREATE INDEX IF NOT EXISTS idx_lead_times_code ON ingredient_lead_times(product_code);"
            ]
            
            for sql in indexes_sql:
                self.cursor.execute(sql)
                
            self.conn.commit()
            logger.info("Tables and indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            self.conn.rollback()
            raise
    
    def load_stock_inventory(self):
        """Load stock inventory data from CSV."""
        try:
            df = self.read_csv_safe('Stock-on-hand.csv', skiprows=1)
            df.columns = ['product_code', 'product_description', 'product_group', 'base_pack', 'allocated', 'on_hand', 'base_unit']
            
            # Clean data
            df = df.dropna(subset=['product_code'])
            df['base_pack'] = pd.to_numeric(df['base_pack'], errors='coerce')
            df['allocated'] = pd.to_numeric(df['allocated'], errors='coerce')
            df['on_hand'] = pd.to_numeric(df['on_hand'], errors='coerce')
            
            # Clear existing data
            self.cursor.execute("DELETE FROM stock_inventory;")
            
            # Insert data
            insert_sql = """
                INSERT INTO stock_inventory (product_code, product_description, product_group, base_pack, allocated, on_hand, base_unit)
                VALUES %s
            """
            
            data_tuples = [tuple(row) for row in df.to_numpy()]
            execute_values(self.cursor, insert_sql, data_tuples)
            
            self.conn.commit()
            logger.info(f"Loaded {len(df)} stock inventory records")
            
        except Exception as e:
            logger.error(f"Error loading stock inventory: {e}")
            self.conn.rollback()
            raise
    
    def load_sales_history(self):
        """Load and transform sales history data from CSV."""
        try:
            df = self.read_csv_safe('Past-sales.csv')
            
            # Remove BOM character if present
            df.columns = [col.lstrip('\ufeff') for col in df.columns]
            
            # Filter out total rows
            df = df[df['Product'] != 'Total'].copy()
            
            # Transform from wide to long format
            month_columns = [col for col in df.columns if col not in ['Shop', 'Region', 'Product']]
            
            sales_data = []
            for _, row in df.iterrows():
                for month_col in month_columns:
                    if pd.notna(row[month_col]) and row[month_col] != '':
                        try:
                            # Parse month-year format (e.g., "Jun-24" to "2024-06-01")
                            month_parts = month_col.split('-')
                            if len(month_parts) == 2:
                                month_name, year = month_parts
                                year = f"20{year}" if len(year) == 2 else year
                                month_date = datetime.strptime(f"{month_name}-{year}", "%b-%Y").date()
                                
                                sales_data.append({
                                    'shop': row['Shop'],
                                    'region': row['Region'],
                                    'product': row['Product'],
                                    'sale_month': month_date,
                                    'quantity': int(row[month_col])
                                })
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Skipping invalid sales data: {row[month_col]} for {month_col}")
                            continue
            
            # Clear existing data
            self.cursor.execute("DELETE FROM sales_history;")
            
            # Insert data
            insert_sql = """
                INSERT INTO sales_history (shop, region, product, sale_month, quantity)
                VALUES %s
            """
            
            data_tuples = [(d['shop'], d['region'], d['product'], d['sale_month'], d['quantity']) for d in sales_data]
            execute_values(self.cursor, insert_sql, data_tuples)
            
            self.conn.commit()
            logger.info(f"Loaded {len(sales_data)} sales history records")
            
        except Exception as e:
            logger.error(f"Error loading sales history: {e}")
            self.conn.rollback()
            raise
    
    def load_products_and_ingredients(self):
        """Load product ingredients from Red, Black, and Gold CSV files."""
        try:
            # Insert products first
            products = ['Red', 'Black', 'Gold']
            self.cursor.execute("DELETE FROM product_ingredients;")
            self.cursor.execute("DELETE FROM products;")
            
            for product in products:
                self.cursor.execute("INSERT INTO products (product_name) VALUES (%s) ON CONFLICT (product_name) DO NOTHING;", (product,))
            
            self.conn.commit()
            
            # Load ingredients for each product
            for product_name in products:
                filename = f'{product_name}-ingredients-edited.csv'
                try:
                    df = self.read_csv_safe(filename)
                    
                    # Remove BOM character if present
                    df.columns = [col.lstrip('\ufeff') for col in df.columns]
                    
                    # Get product ID
                    self.cursor.execute("SELECT id FROM products WHERE product_name = %s;", (product_name,))
                    product_id = self.cursor.fetchone()[0]
                    
                    # Clean and prepare data
                    ingredient_data = []
                    for _, row in df.iterrows():
                        # Skip rows with 'Delete' in last column
                        if len(df.columns) > 8 and str(row.iloc[-1]).strip().lower() == 'delete':
                            continue
                            
                        ingredient_data.append({
                            'product_id': product_id,
                            'component': row.get('Components', ''),
                            'parent_component': row.get('Parent-component', ''),
                            'intermediate_component': row.get('Intermediate-component', ''),
                            'quantity': pd.to_numeric(row.get('quantity', 0), errors='coerce') or 0,
                            'wastage': pd.to_numeric(row.get('wastage', 0), errors='coerce') or 0,
                            'unit': row.get('unit', ''),
                            'unit_cost': pd.to_numeric(row.get('unit cost', 0), errors='coerce') or 0,
                            'total_cost': pd.to_numeric(row.get('total cost', 0), errors='coerce') or 0
                        })
                    
                    # Insert ingredient data
                    insert_sql = """
                        INSERT INTO product_ingredients 
                        (product_id, component, parent_component, intermediate_component, quantity, wastage, unit, unit_cost, total_cost)
                        VALUES %s
                    """
                    
                    data_tuples = [(
                        d['product_id'], d['component'], d['parent_component'], d['intermediate_component'],
                        d['quantity'], d['wastage'], d['unit'], d['unit_cost'], d['total_cost']
                    ) for d in ingredient_data]
                    
                    execute_values(self.cursor, insert_sql, data_tuples)
                    logger.info(f"Loaded {len(ingredient_data)} ingredient records for {product_name}")
                    
                except FileNotFoundError:
                    logger.warning(f"File {filename} not found, skipping")
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
                    raise
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error loading products and ingredients: {e}")
            self.conn.rollback()
            raise
    
    def load_ingredient_lead_times(self):
        """Load ingredient lead times data."""
        try:
            df = self.read_csv_safe('Ingredient-lead-times.csv', skiprows=1)
            # Handle trailing empty column
            if len(df.columns) == 7:
                df = df.iloc[:, :6]  # Keep only first 6 columns
            df.columns = ['product_code', 'product_description', 'product_group', 'minimum_order_quantity', 'lead_time_days', 'base_unit']
            
            # Clean data
            df = df.dropna(subset=['product_code'])
            
            # Parse minimum order quantity (remove commas)
            df['minimum_order_quantity'] = df['minimum_order_quantity'].astype(str).str.replace(',', '').replace('nan', '0')
            df['minimum_order_quantity'] = pd.to_numeric(df['minimum_order_quantity'], errors='coerce').fillna(0).astype(int)
            
            df['lead_time_days'] = pd.to_numeric(df['lead_time_days'], errors='coerce').fillna(0).astype(int)
            
            # Clear existing data
            self.cursor.execute("DELETE FROM ingredient_lead_times;")
            
            # Insert data
            insert_sql = """
                INSERT INTO ingredient_lead_times (product_code, product_description, product_group, minimum_order_quantity, lead_time_days, base_unit)
                VALUES %s
            """
            
            data_tuples = [tuple(row) for row in df.to_numpy()]
            execute_values(self.cursor, insert_sql, data_tuples)
            
            self.conn.commit()
            logger.info(f"Loaded {len(df)} ingredient lead time records")
            
        except Exception as e:
            logger.error(f"Error loading ingredient lead times: {e}")
            self.conn.rollback()
            raise
    
    def run_data_quality_checks(self):
        """Run basic data quality checks and report statistics."""
        try:
            checks = [
                ("Stock Inventory", "SELECT COUNT(*) FROM stock_inventory;"),
                ("Sales History", "SELECT COUNT(*) FROM sales_history;"),
                ("Products", "SELECT COUNT(*) FROM products;"),
                ("Product Ingredients", "SELECT COUNT(*) FROM product_ingredients;"),
                ("Ingredient Lead Times", "SELECT COUNT(*) FROM ingredient_lead_times;"),
                ("Sales by Product", "SELECT product, SUM(quantity) FROM sales_history GROUP BY product ORDER BY SUM(quantity) DESC;"),
                ("Ingredients by Product", "SELECT p.product_name, COUNT(*) FROM products p JOIN product_ingredients pi ON p.id = pi.product_id GROUP BY p.product_name;")
            ]
            
            logger.info("=== DATA QUALITY REPORT ===")
            for check_name, sql in checks:
                self.cursor.execute(sql)
                results = self.cursor.fetchall()
                logger.info(f"{check_name}: {results}")
                
        except Exception as e:
            logger.error(f"Error running data quality checks: {e}")
    
    def close_connection(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

def main():
    """Main execution function."""
    loader = ManufacturingDataLoader()
    
    try:
        # Connect to database
        loader.connect_to_db()
        
        # Drop existing tables and create new schema
        logger.info("Dropping existing tables...")
        loader.drop_tables()
        
        logger.info("Creating database schema...")
        loader.create_tables()
        
        # Load data
        logger.info("Loading stock inventory...")
        loader.load_stock_inventory()
        
        logger.info("Loading sales history...")
        loader.load_sales_history()
        
        logger.info("Loading products and ingredients...")
        loader.load_products_and_ingredients()
        
        logger.info("Loading ingredient lead times...")
        loader.load_ingredient_lead_times()
        
        # Run quality checks
        logger.info("Running data quality checks...")
        loader.run_data_quality_checks()
        
        logger.info("Data loading completed successfully!")
        
    except Exception as e:
        logger.error(f"Data loading failed: {e}")
        raise
    finally:
        loader.close_connection()

if __name__ == "__main__":
    main()