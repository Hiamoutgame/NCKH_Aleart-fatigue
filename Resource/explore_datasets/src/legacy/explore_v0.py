"""LEGACY: script explore dau tien. Xem src/shared/ cho ban chuan hoa."""

# Example exploration script
import pandas as pd
import os

def load_dataset(filepath):
    """Load a dataset from CSV, JSON, or Parquet based on extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        return pd.read_csv(filepath)
    elif ext == '.json':
        return pd.read_json(filepath)
    elif ext == '.parquet':
        return pd.read_parquet(filepath)
    else:
        raise ValueError(f'Unsupported file type: {ext}')

def explore_dataset(df, name='Dataset'):
    print(f'=== {name} ===')
    print(f'Shape: {df.shape}')
    print('\nColumns:')
    print(df.dtypes)
    print('\nFirst 10 rows:')
    print(df.head(10))
    print('\nValue counts for service column (if exists):')
    if 'service' in df.columns:
        print(df['service'].value_counts().head())
    else:
        print('No service column')
    print('\nValue counts for message column (if exists):')
    if 'message' in df.columns:
        print(df['message'].value_counts().head())
    else:
        print('No message column')

if __name__ == '__main__':
    # Example usage:
    # df = load_dataset('path/to/dataset.csv')
    # explore_dataset(df)
    pass
