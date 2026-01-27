""" tests/mocks/utils.py

Data quality degradation utilities. Inject realistic data quality issues for testing data cleaning agents.
"""

import pandas as pd
import numpy as np
from typing import List, Callable, Tuple, Any, Optional
from datetime import datetime, timedelta
import random
import string
from enum import Enum


class DegradationType(Enum):
    """Types of data quality degradation."""
    MISSING_VALUES = "missing_values"
    DUPLICATES = "duplicates"
    OUTLIERS = "outliers"
    TYPE_INCONSISTENCY = "type_inconsistency"
    FORMATTING_ISSUES = "formatting_issues"
    RANGE_VIOLATIONS = "range_violations"
    WHITESPACE_ISSUES = "whitespace_issues"
    ENCODING_ISSUES = "encoding_issues"
    DATE_INCONSISTENCY = "date_inconsistency"
    CATEGORICAL_TYPOS = "categorical_typos"


class DataDegradation:
    """Inject realistic data quality issues into clean datasets."""

    def __init__(self, seed: int = 42):
        """Initialize with optional seed for reproducibility."""
        np.random.seed(seed)
        random.seed(seed)

    # ============================================================
    # MISSING VALUES
    # ============================================================

    def inject_missing_values(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        missing_rate: float = 0.10,
        pattern: str = "random"
    ) -> pd.DataFrame:
        """
        Inject missing values with different patterns.

        Args:
            df: Input DataFrame
            columns: Columns to degrade (None = all)
            missing_rate: Proportion of values to remove (0-1)
            pattern: 'random', 'mcar' (Missing Completely At Random),
                    'mar' (Missing At Random), 'mnar' (Missing Not At Random)

        Returns:
            DataFrame with missing values injected
        """

        df = df.copy()
        cols = columns or df.select_dtypes(include=['float', 'object']).columns

        for col in cols:
            if col not in df.columns:
                continue

            n_missing = int(len(df) * missing_rate)

            if pattern == "random":
                # Completely random missingness
                missing_idx = np.random.choice(df.index, n_missing, replace=False)
                df.loc[missing_idx, col] = np.nan

            elif pattern == "mcar":
                # Missing Completely At Random (no bias)
                missing_idx = np.random.choice(df.index, n_missing, replace=False)
                df.loc[missing_idx, col] = np.nan

            elif pattern == "mar":
                # Missing At Random - depends on another column
                if len(df.columns) > 1:
                    ref_col = df.columns[np.random.randint(0, len(df.columns))]
                    threshold = df[ref_col].quantile(0.5) if pd.api.types.is_numeric_dtype(df[ref_col]) else None
                    if threshold is not None:
                        mask = df[ref_col] > threshold
                        candidates = df[mask].index
                        missing_idx = np.random.choice(candidates, min(n_missing, len(candidates)), replace=False)
                        df.loc[missing_idx, col] = np.nan

            elif pattern == "mnar":
                # Missing Not At Random - depends on column itself
                if pd.api.types.is_numeric_dtype(df[col]):
                    # Missing high values
                    threshold = df[col].quantile(0.75)
                    candidates = df[df[col] > threshold].index
                    missing_idx = np.random.choice(candidates, min(n_missing, len(candidates)), replace=False)
                    df.loc[missing_idx, col] = np.nan

        return df

    # ============================================================
    # DUPLICATES
    # ============================================================

    def inject_duplicates(
        self,
        df: pd.DataFrame,
        dup_rate: float = 0.05,
        type_: str = "exact"
    ) -> pd.DataFrame:
        """
        Inject duplicate rows.

        Args:
            df: Input DataFrame
            dup_rate: Proportion of duplicates (0-1)
            type_: 'exact' (full row duplicates), 'partial' (some columns differ),
                   'delayed' (duplicate appears later in time)

        Returns:
            DataFrame with duplicates
        """

        df = df.copy()
        n_dups = int(len(df) * dup_rate)

        if type_ == "exact":
            # Exact duplicates
            dup_idx = np.random.choice(df.index, n_dups, replace=False)
            duplicates = df.loc[dup_idx].copy()
            df = pd.concat([df, duplicates], ignore_index=True)

        elif type_ == "partial":
            # Duplicate some columns only
            dup_idx = np.random.choice(df.index, n_dups, replace=False)
            duplicates = df.loc[dup_idx].copy()

            # Modify some columns
            for col in duplicates.select_dtypes(include=['float', 'int']).columns:
                duplicates[col] = duplicates[col] + np.random.normal(0, 1, len(duplicates))

            df = pd.concat([df, duplicates], ignore_index=True)

        elif type_ == "delayed":
            # Duplicate appears later in time (if timestamp exists)
            timestamp_cols = df.select_dtypes(include=['datetime64']).columns
            if len(timestamp_cols) > 0:
                ts_col = timestamp_cols[0]
                dup_idx = np.random.choice(df.index, n_dups, replace=False)
                duplicates = df.loc[dup_idx].copy()

                # Shift timestamp forward
                duplicates[ts_col] = duplicates[ts_col] + timedelta(days=random.randint(1, 7))
                df = pd.concat([df, duplicates], ignore_index=True)

        return df.reset_index(drop=True)

    # ============================================================
    # OUTLIERS
    # ============================================================

    def inject_outliers(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        outlier_rate: float = 0.02,
        method: str = "extreme"
    ) -> pd.DataFrame:
        """
        Inject outliers in numeric columns.

        Args:
            df: Input DataFrame
            columns: Columns to degrade (None = numeric only)
            outlier_rate: Proportion of outliers (0-1)
            method: 'extreme' (very high/low), 'iqr' (beyond IQR), 'impossible' (biologically impossible)

        Returns:
            DataFrame with outliers
        """

        df = df.copy()
        cols = columns or df.select_dtypes(include=['int', 'float']).columns

        for col in cols:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue

            n_outliers = int(len(df) * outlier_rate)
            outlier_idx = np.random.choice(df.index, n_outliers, replace=False)

            if method == "extreme":
                # Multiply by extreme factor
                df.loc[outlier_idx, col] = df[col].max() * np.random.uniform(5, 100, n_outliers)

            elif method == "iqr":
                # Beyond 3x IQR
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                df.loc[outlier_idx, col] = Q3 + 3 * IQR

            elif method == "impossible":
                # Impossible values (negative for normally positive, > 100% for percentages)
                if "price" in col.lower() or "cost" in col.lower():
                    df.loc[outlier_idx, col] = -abs(df[col].max())
                elif "percentage" in col.lower() or "pct" in col.lower():
                    df.loc[outlier_idx, col] = np.random.uniform(100, 1000, n_outliers)
                else:
                    df.loc[outlier_idx, col] = -abs(df[col].max()) * np.random.uniform(1, 10, n_outliers)

        return df

    # ============================================================
    # TYPE INCONSISTENCY
    # ============================================================

    def inject_type_inconsistency(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        inconsistency_rate: float = 0.05
    ) -> pd.DataFrame:
        """
        Convert some numeric values to strings or vice versa.

        Args:
            df: Input DataFrame
            columns: Columns to degrade (None = numeric only)
            inconsistency_rate: Proportion affected (0-1)

        Returns:
            DataFrame with type inconsistencies (still object dtype)
        """

        df = df.copy()
        cols = columns or df.select_dtypes(include=['int', 'float']).columns

        for col in cols:
            if col not in df.columns:
                continue

            # Convert to object type
            df[col] = df[col].astype(str)

            n_inconsistent = int(len(df) * inconsistency_rate)
            inconsistent_idx = np.random.choice(df.index, n_inconsistent, replace=False)

            # Replace some with invalid types
            for idx in inconsistent_idx:
                choice = random.choice([
                    'N/A', 'NULL', 'unknown', '#ERROR', '--',
                    'n/a', 'UNKNOWN', 'na', ''
                ])
                df.loc[idx, col] = choice

        return df

    # ============================================================
    # FORMATTING ISSUES
    # ============================================================

    def inject_formatting_issues(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        format_rate: float = 0.10
    ) -> pd.DataFrame:
        """
        Inject formatting inconsistencies (case, whitespace, punctuation).

        Args:
            df: Input DataFrame
            columns: Columns to degrade (None = object only)
            format_rate: Proportion affected (0-1)

        Returns:
            DataFrame with formatting issues
        """

        df = df.copy()
        cols = columns or df.select_dtypes(include=['object']).columns

        for col in cols:
            if col not in df.columns:
                continue

            n_format = int(len(df) * format_rate)
            format_idx = np.random.choice(df.index, n_format, replace=False)

            for idx in format_idx:
                val = str(df.loc[idx, col])

                # Random formatting change
                choice = random.choice([
                    lambda x: x.upper(),
                    lambda x: x.lower(),
                    lambda x: x.title(),
                    lambda x: ' ' + x + ' ',  # Extra whitespace
                    lambda x: x.replace(' ', '  '),  # Double spaces
                    lambda x: x.strip(),  # Remove leading/trailing
                ])

                try:
                    df.loc[idx, col] = choice(val)
                except:
                    pass

        return df

    # ============================================================
    # RANGE VIOLATIONS
    # ============================================================

    def inject_range_violations(
        self,
        df: pd.DataFrame,
        column_ranges: dict,  # {"column_name": (min, max)}
        violation_rate: float = 0.05
    ) -> pd.DataFrame:
        """
        Inject values outside expected ranges.

        Args:
            df: Input DataFrame
            column_ranges: Dict of column_name -> (min, max) tuple
            violation_rate: Proportion affected (0-1)

        Returns:
            DataFrame with range violations
        """

        df = df.copy()

        for col, (min_val, max_val) in column_ranges.items():
            if col not in df.columns:
                continue

            n_violations = int(len(df) * violation_rate)
            violation_idx = np.random.choice(df.index, n_violations, replace=False)

            # Generate out-of-range values
            for idx in violation_idx:
                if random.random() > 0.5:
                    df.loc[idx, col] = min_val - np.random.uniform(1, 100)
                else:
                    df.loc[idx, col] = max_val + np.random.uniform(1, 100)

        return df

    # ============================================================
    # WHITESPACE ISSUES
    # ============================================================

    def inject_whitespace_issues(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        whitespace_rate: float = 0.08
    ) -> pd.DataFrame:
        """
        Inject whitespace issues: leading/trailing spaces, tabs, etc.

        Args:
            df: Input DataFrame
            columns: Columns to degrade (None = object only)
            whitespace_rate: Proportion affected (0-1)

        Returns:
            DataFrame with whitespace issues
        """

        df = df.copy()
        cols = columns or df.select_dtypes(include=['object']).columns

        for col in cols:
            if col not in df.columns:
                continue

            n_ws = int(len(df) * whitespace_rate)
            ws_idx = np.random.choice(df.index, n_ws, replace=False)

            for idx in ws_idx:
                val = str(df.loc[idx, col])

                choice = random.choice([
                    lambda x: ' ' * random.randint(1, 5) + x,  # Leading spaces
                    lambda x: x + ' ' * random.randint(1, 5),  # Trailing spaces
                    lambda x: '\t' + x,  # Tab character
                    lambda x: x.replace(' ', '\t'),  # Replace spaces with tabs
                    lambda x: x.replace(' ', '  '),  # Double spaces
                ])

                df.loc[idx, col] = choice(val)

        return df

    # ============================================================
    # DATE INCONSISTENCY
    # ============================================================

    def inject_date_inconsistency(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        date_rate: float = 0.05
    ) -> pd.DataFrame:
        """
        Inject date format inconsistencies and future/past dates.

        Args:
            df: Input DataFrame
            columns: Datetime columns (None = auto-detect)
            date_rate: Proportion affected (0-1)

        Returns:
            DataFrame with date issues
        """

        df = df.copy()
        cols = columns or df.select_dtypes(include=['datetime64']).columns

        for col in cols:
            if col not in df.columns:
                continue

            n_date = int(len(df) * date_rate)
            date_idx = np.random.choice(df.index, n_date, replace=False)

            for idx in date_idx:
                # Convert to string with wrong format
                val = df.loc[idx, col]

                choice = random.choice([
                    lambda x: x.strftime('%d/%m/%Y'),  # Different format
                    lambda x: x.strftime('%Y-%m-%d').split('-')[np.random.randint(0, 3)],  # Partial date
                    lambda x: x + timedelta(days=random.randint(365, 3650)),  # Future date
                    lambda x: x - timedelta(days=random.randint(365, 10000)),  # Very old date
                    lambda x: str(x).replace('-', '/'),  # Format change
                ])

                try:
                    df.loc[idx, col] = choice(val)
                except:
                    pass

        return df

    # ============================================================
    # CATEGORICAL TYPOS
    # ============================================================

    def inject_categorical_typos(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        typo_rate: float = 0.05
    ) -> pd.DataFrame:
        """
        Inject common typos in categorical columns.

        Args:
            df: Input DataFrame
            columns: Categorical columns (None = object only)
            typo_rate: Proportion affected (0-1)

        Returns:
            DataFrame with typos
        """

        df = df.copy()
        cols = columns or df.select_dtypes(include=['object']).columns

        for col in cols:
            if col not in df.columns:
                continue

            n_typos = int(len(df) * typo_rate)
            typo_idx = np.random.choice(df.index, n_typos, replace=False)

            for idx in typo_idx:
                val = str(df.loc[idx, col])

                # Apply typo transformation
                choice = random.choice([
                    lambda x: x.replace('e', '3'),  # Letter to number
                    lambda x: x.replace('a', '@'),  # Special char
                    lambda x: x.replace('o', '0'),  # O to zero
                    lambda x: x[:-1] if len(x) > 1 else x,  # Missing last char
                    lambda x: x + random.choice(string.ascii_lowercase),  # Extra char
                    lambda x: ''.join(random.sample(x, min(len(x), len(x)))),  # Scrambled
                ])

                try:
                    df.loc[idx, col] = choice(val)
                except:
                    pass

        return df

    # ============================================================
    # COMBINED DEGRADATION
    # ============================================================

    def degrade_dataset(
        self,
        df: pd.DataFrame,
        degradation_specs: dict,
        apply_order: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Apply multiple degradation types to dataset.

        Args:
            df: Input DataFrame
            degradation_specs: Dict of degradation_type -> kwargs
                Example:
                {
                    'missing_values': {'missing_rate': 0.10},
                    'duplicates': {'dup_rate': 0.05},
                    'outliers': {'outlier_rate': 0.02},
                }
            apply_order: Order to apply degradations (None = default order)

        Returns:
            Degraded DataFrame
        """

        df = df.copy()

        default_order = [
            'missing_values',
            'type_inconsistency',
            'whitespace_issues',
            'categorical_typos',
            'formatting_issues',
            'outliers',
            'range_violations',
            'date_inconsistency',
            'duplicates',
        ]

        order = apply_order or default_order

        for degradation_type in order:
            if degradation_type not in degradation_specs:
                continue

            kwargs = degradation_specs[degradation_type]

            if degradation_type == 'missing_values':
                df = self.inject_missing_values(df, **kwargs)
            elif degradation_type == 'duplicates':
                df = self.inject_duplicates(df, **kwargs)
            elif degradation_type == 'outliers':
                df = self.inject_outliers(df, **kwargs)
            elif degradation_type == 'type_inconsistency':
                df = self.inject_type_inconsistency(df, **kwargs)
            elif degradation_type == 'formatting_issues':
                df = self.inject_formatting_issues(df, **kwargs)
            elif degradation_type == 'range_violations':
                df = self.inject_range_violations(df, **kwargs)
            elif degradation_type == 'whitespace_issues':
                df = self.inject_whitespace_issues(df, **kwargs)
            elif degradation_type == 'date_inconsistency':
                df = self.inject_date_inconsistency(df, **kwargs)
            elif degradation_type == 'categorical_typos':
                df = self.inject_categorical_typos(df, **kwargs)

        return df

    # ============================================================
    # REPORT GENERATION
    # ============================================================

    def generate_degradation_report(self, df_clean: pd.DataFrame, df_dirty: pd.DataFrame) -> dict:
        """
        Generate report on degradation applied.

        Args:
            df_clean: Original clean DataFrame
            df_dirty: Degraded DataFrame

        Returns:
            Dict with degradation statistics
        """

        report = {
            "shape_change": {
                "original": df_clean.shape,
                "degraded": df_dirty.shape,
            },
            "missing_values": {
                col: {
                    "clean": df_clean[col].isna().sum(),
                    "dirty": df_dirty[col].isna().sum(),
                }
                for col in df_clean.columns
            },
            "duplicates": {
                "original": df_clean.duplicated().sum(),
                "degraded": df_dirty.duplicated().sum(),
            },
            "type_changes": {
                col: {
                    "clean": str(df_clean[col].dtype),
                    "dirty": str(df_dirty[col].dtype),
                }
                for col in df_clean.columns
            },
        }

        return report


# ============================================================
# USAGE EXAMPLES
# ============================================================

if __name__ == "__main__":
    from .createMock import MockDataGenerator
    import json

    # Generate clean data
    gen = MockDataGenerator(seed=42)
    df_clean = gen.generate_cafe_sales(n_rows=100, dirty=False)

    print("📊 Original clean data:")
    print(df_clean.head())
    print(f"\nShape: {df_clean.shape}")
    print(f"Missing values: {df_clean.isna().sum().sum()}\n")

    # ============================================================
    # APPLY INDIVIDUAL DEGRADATIONS
    # ============================================================

    degrader = DataDegradation(seed=42)

    # Missing values
    print("🌪️  Injecting missing values...")
    df_missing = degrader.inject_missing_values(df_clean, missing_rate=0.15)
    print(f"Missing values: {df_missing.isna().sum().sum()}\n")

    # Outliers
    print("📈 Injecting outliers...")
    df_outliers = degrader.inject_outliers(df_clean, outlier_rate=0.05, method="extreme")
    print(f"Max values: {df_outliers.select_dtypes(include=['float']).max()}\n")

    # Duplicates
    print("📋 Injecting duplicates...")
    df_dups = degrader.inject_duplicates(df_clean, dup_rate=0.10)
    print(f"Shape: {df_dups.shape}")
    print(f"Duplicates: {df_dups.duplicated().sum()}\n")

    # Type inconsistency
    print("🔤 Injecting type inconsistencies...")
    df_types = degrader.inject_type_inconsistency(df_clean, inconsistency_rate=0.10)
    print(df_types.head())\n")

    # ============================================================
    # APPLY COMBINED DEGRADATION
    # ============================================================

    print("\n\n🔨 Applying comprehensive degradation...")
    degradation_specs = {
        'missing_values': {'missing_rate': 0.10, 'pattern': 'random'},
        'duplicates': {'dup_rate': 0.05, 'type_': 'exact'},
        'outliers': {'outlier_rate': 0.02, 'method': 'extreme'},
        'type_inconsistency': {'inconsistency_rate': 0.05},
        'formatting_issues': {'format_rate': 0.08},
        'categorical_typos': {'typo_rate': 0.05},
        'whitespace_issues': {'whitespace_rate': 0.08},
    }

    df_degraded = degrader.degrade_dataset(df_clean, degradation_specs)

    # Generate report
    report = degrader.generate_degradation_report(df_clean, df_degraded)

    print("\n📊 Degradation Report:")
    print(json.dumps(report, indent=2, default=str))

    # Save
    df_degraded.to_csv('mock_cafe_sales_degraded.csv', index=False)
    print("\n✅ Saved mock_cafe_sales_degraded.csv")
