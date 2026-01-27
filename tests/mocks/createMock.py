# core/mock_data.py
"""
Mock data generation for testing and development.
"""

import pandas as pd
import numpy as np
from typing import List
import random
import string

DEFAULT_SEED = 42
class MockDataGenerator:
    """Generate realistic mock datasets for testing agent workflows."""

    def __init__(self, seed: int = DEFAULT_SEED):
        """Initialize with optional seed for reproducibility."""
        np.random.seed(seed)
        random.seed(seed)

    def generate_cafe_sales(self, n_rows: int = 1000, dirty: bool = True) -> pd.DataFrame:
        """
        Generate café sales dataset with optional data quality issues.

        Args:
            n_rows: Number of sales records
            dirty: If True, introduce realistic data quality issues

        Returns:
            DataFrame with café sales data
        """

        dates = pd.date_range(start='2023-01-01', periods=n_rows, freq='H')

        data = {
            'transaction_id': [f'TXN_{i:06d}' for i in range(n_rows)],
            'timestamp': dates,
            'customer_name': np.random.choice([
                'Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank',
                'Grace', 'Henry', 'Iris', 'Jack'
            ], n_rows),
            'product': np.random.choice([
                'Espresso', 'Latte', 'Cappuccino', 'Americano', 'Macchiato',
                'Mocha', 'Flat White', 'Cortado', 'Ristretto', 'Affogato'
            ], n_rows),
            'quantity': np.random.randint(1, 5, n_rows),
            'unit_price': np.random.uniform(3.0, 8.0, n_rows),
            'total_sale': None,  # Will compute
            'payment_method': np.random.choice(['Cash', 'Card', 'Mobile'], n_rows),
            'location': np.random.choice(['Downtown', 'Airport', 'Mall', 'Office'], n_rows),
        }

        data['total_sale'] = data['quantity'] * data['unit_price']

        df = pd.DataFrame(data)

        if dirty:
            df = self._inject_data_quality_issues(df, [
                'missing_values',
                'duplicates',
                'outliers',
                'inconsistent_types',
                'formatting_issues',
            ])

        return df

    def generate_ecommerce_orders(self, n_rows: int = 500, dirty: bool = True) -> pd.DataFrame:
        """
        Generate e-commerce order dataset.

        Args:
            n_rows: Number of orders
            dirty: If True, introduce data quality issues

        Returns:
            DataFrame with order data
        """

        order_ids = [f'ORD_{i:07d}' for i in range(n_rows)]
        customers = [f'CUST_{i:06d}' for i in range(1, n_rows // 10)]

        data = {
            'order_id': order_ids,
            'customer_id': np.random.choice(customers, n_rows),
            'order_date': pd.date_range('2023-01-01', periods=n_rows, freq='D'),
            'product_category': np.random.choice(
                ['Electronics', 'Clothing', 'Home', 'Sports', 'Books'], n_rows
            ),
            'product_price': np.random.uniform(10, 500, n_rows),
            'quantity': np.random.randint(1, 10, n_rows),
            'discount_percentage': np.random.uniform(0, 50, n_rows),
            'shipping_cost': np.random.uniform(5, 50, n_rows),
            'order_status': np.random.choice(
                ['Pending', 'Shipped', 'Delivered', 'Cancelled'], n_rows
            ),
            'payment_status': np.random.choice(['Paid', 'Pending', 'Failed'], n_rows),
        }

        df = pd.DataFrame(data)
        df['total_amount'] = (df['product_price'] * df['quantity'] *
                             (1 - df['discount_percentage']/100) +
                             df['shipping_cost'])

        if dirty:
            df = self._inject_data_quality_issues(df, [
                'missing_values',
                'duplicates',
                'outliers',
                'inconsistent_types',
            ])

        return df

    def generate_customer_data(self, n_rows: int = 200, dirty: bool = True) -> pd.DataFrame:
        """
        Generate customer database with messy data.

        Args:
            n_rows: Number of customers
            dirty: If True, introduce data quality issues

        Returns:
            DataFrame with customer data
        """

        data = {
            'customer_id': [f'CUST_{i:06d}' for i in range(n_rows)],
            'first_name': np.random.choice(
                ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Emma', 'Robert', 'Lisa'],
                n_rows
            ),
            'last_name': np.random.choice(
                ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller'],
                n_rows
            ),
            'email': [f'user_{i}@example.com' for i in range(n_rows)],
            'phone': [f'+1-{np.random.randint(200, 999)}-{np.random.randint(200, 999)}-{np.random.randint(1000, 9999)}'
                     for _ in range(n_rows)],
            'signup_date': pd.date_range('2022-01-01', periods=n_rows, freq='D'),
            'country': np.random.choice(['USA', 'UK', 'Canada', 'Australia', 'Germany'], n_rows),
            'lifetime_value': np.random.uniform(0, 10000, n_rows),
            'is_active': np.random.choice([True, False], n_rows),
        }

        df = pd.DataFrame(data)

        if dirty:
            df = self._inject_data_quality_issues(df, [
                'missing_values',
                'duplicates',
                'inconsistent_types',
                'formatting_issues',
            ])

        return df

    def generate_sensor_data(self, n_rows: int = 5000, dirty: bool = True) -> pd.DataFrame:
        """
        Generate IoT sensor readings with realistic patterns.

        Args:
            n_rows: Number of sensor readings
            dirty: If True, introduce data quality issues

        Returns:
            DataFrame with sensor data
        """

        sensors = [f'SENSOR_{i:03d}' for i in range(10)]
        timestamps = pd.date_range('2023-01-01', periods=n_rows, freq='1min')

        # Create realistic temperature pattern (sine wave + noise)
        base_temp = 20 + 10 * np.sin(np.arange(n_rows) / 100)

        data = {
            'sensor_id': np.random.choice(sensors, n_rows),
            'timestamp': timestamps,
            'temperature': base_temp + np.random.normal(0, 2, n_rows),
            'humidity': np.random.uniform(30, 80, n_rows),
            'pressure': np.random.uniform(990, 1010, n_rows),
            'status': np.random.choice(['OK', 'WARNING', 'ERROR'], n_rows, p=[0.85, 0.10, 0.05]),
        }

        df = pd.DataFrame(data)

        if dirty:
            df = self._inject_data_quality_issues(df, [
                'missing_values',
                'outliers',
                'inconsistent_types',
            ])

        return df

    def _inject_data_quality_issues(self, df: pd.DataFrame, issues: List[str]) -> pd.DataFrame:
        """Inject realistic data quality issues for testing."""

        df = df.copy()

        if 'missing_values' in issues:
            # Random missing values in non-critical columns
            for col in df.select_dtypes(include=['float', 'object']).columns:
                if random.random() > 0.7:
                    missing_rate = random.uniform(0.05, 0.20)
                    missing_idx = np.random.choice(df.index, int(len(df) * missing_rate), replace=False)
                    df.loc[missing_idx, col] = np.nan

        if 'duplicates' in issues:
            # Introduce duplicate rows
            dup_count = int(len(df) * 0.05)
            dup_indices = np.random.choice(df.index, dup_count, replace=False)
            df = pd.concat([df, df.loc[dup_indices]], ignore_index=True)

        if 'outliers' in issues:
            # Inject outliers in numeric columns
            for col in df.select_dtypes(include=['float', 'int']).columns:
                outlier_indices = np.random.choice(df.index, int(len(df) * 0.02), replace=False)
                df.loc[outlier_indices, col] = df[col].max() * 10

        if 'inconsistent_types' in issues:
            # Convert some numeric columns to strings inconsistently
            for col in df.select_dtypes(include=['int']).columns:
                inconsistent_idx = np.random.choice(df.index, int(len(df) * 0.05), replace=False)
                df.loc[inconsistent_idx, col] = df.loc[inconsistent_idx, col].astype(str)

        if 'formatting_issues' in issues:
            # Inconsistent formatting in text columns
            for col in df.select_dtypes(include=['object']).columns:
                inconsistent_idx = np.random.choice(df.index, int(len(df) * 0.10), replace=False)
                df.loc[inconsistent_idx, col] = df.loc[inconsistent_idx, col].str.upper()

        return df.reset_index(drop=True)

    def generate_schema_validation_errors(self, df: pd.DataFrame, error_rate: float = 0.1) -> pd.DataFrame:
        """Add schema validation errors to dataset."""

        df = df.copy()

        # Wrong types
        for col in df.select_dtypes(include=['int']).columns:
            if random.random() < error_rate:
                error_idx = np.random.choice(df.index, int(len(df) * 0.05), replace=False)
                df.loc[error_idx, col] = 'invalid_' + str(random.randint(1, 100))

        return df

if __name__ == "__main__":
    generator = MockDataGenerator(seed=42)

    # Generate clean data
    print("🧹 Generating clean café sales data...")
    df_clean = generator.generate_cafe_sales(n_rows=500, dirty=False)
    print(df_clean.head())
    print(f"\nShape: {df_clean.shape}")

    # Generate dirty data (for testing data cleaning agents)
    print("\n\n🌪️  Generating dirty café sales data...")
    df_dirty = generator.generate_cafe_sales(n_rows=500, dirty=True)
    print(df_dirty.head())
    print(f"\nMissing values:\n{df_dirty.isna().sum()}")
    print(f"\nDuplicates: {df_dirty.duplicated().sum()}")

    # Generate other datasets
    print("\n\n📦 Generating e-commerce data...")
    df_orders = generator.generate_ecommerce_orders(n_rows=200, dirty=True)
    print(df_orders.head())

    print("\n\n👥 Generating customer data...")
    df_customers = generator.generate_customer_data(n_rows=100, dirty=True)
    print(df_customers.head())

    print("\n\n📡 Generating sensor data...")
    df_sensors = generator.generate_sensor_data(n_rows=1000, dirty=True)
    print(df_sensors.head())

    # Save for testing
    df_dirty.to_csv('mock_cafe_sales_dirty.csv', index=False)
    print("\n✅ Saved mock_cafe_sales_dirty.csv")
