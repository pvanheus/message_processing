#!/usr/bin/env python3

# 1. read in Excel file with manual and ChatGPT theme coding
# 2. convert theme names to numbers
# 3. compute Krippendorff's alpha for inter-rater reliability

import argparse
import sys

import pandas as pd
import numpy as np

from krippendorff import alpha

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compute Krippendorff\'s alpha for inter-rater reliability.')
    parser.add_argument('input_file', type=str, help='Path to the input Excel file with theme coding.')
    args = parser.parse_args()

    # Read the Excel file
    try:
        df = pd.read_excel(args.input_file)
    except Exception as e:
        print(f"Error reading the Excel file: {e}", file=sys.stderr)
        sys.exit(1)

    themes = ["adv.impacts", "access.info", "conspiracy", "alt.remedies", "vaccine.comp", "misinfo", "community", "other"]
    # Remove rows with NaN values in 'theme' or 'chatgpt_theme'
    df = df.dropna(subset=['theme', 'chatgpt_theme'])
    # Make list of themes
    found_themes = df['theme'].unique()
    assert all(theme in found_themes for theme in themes), f"Not all themes found in the data: {found_themes}"

    chatgpt_theme_counts = df['chatgpt_theme'].value_counts()
    manual_theme_counts = df['theme'].value_counts()

    # this prints data in a format that can be used in SankeyMATIC to draw a Sankey diagram showing
    # flow of message between theme classifications
    print("START OF SankeyMATIC")

    source_target_df = df.groupby(['theme', 'chatgpt_theme']).count()['id'].unstack(fill_value=0)
    for theme in themes:
        for other_theme in themes:
            count = source_target_df.at[theme, other_theme]
            if count != 0:
                print(f"{theme} H [{count}] {other_theme} C")

    print("END OF SankeyMATIC")
    mismatched_messages_df = df[df['theme'] != df['chatgpt_theme']].groupby('theme').count()
    mismatched_message_count = mismatched_messages_df.loc[:,'id'].sum()
    mismatched_percentage = mismatched_message_count / len(df) * 100
    print(f"Mismatched message counts {mismatched_message_count} ({mismatched_percentage:.2f}%)")
    for theme in themes:
        mismatched_message_count = mismatched_messages_df.at[theme, 'id'] if theme in mismatched_messages_df.index else 0
        manual_count = manual_theme_counts.get(theme, 0)
        mismatched_percentage = (mismatched_message_count / manual_count * 100) if manual_count > 0 else 0
        print(f"Theme: {theme}, ChatGPT Count: {chatgpt_theme_counts.get(theme, 0)}, "
              f"Manual Count: {manual_count} Mismatched Messages: {mismatched_message_count} ({mismatched_percentage:.2f}%)")
    
    # for theme in themes:
    # Convert theme names to numbers
    theme_mapping = {theme: i for i, theme in enumerate(df['theme'].unique())}
    # print(df['theme'].value_counts())
    # print(df['chatgpt_theme'].value_counts())
    df['theme'] = df['theme'].map(theme_mapping)
    df['chatgpt_theme'] = df['chatgpt_theme'].map(theme_mapping)

    reliability_data = np.array([df['theme'].values, df['chatgpt_theme'].values])
    # Compute Krippendorff's alpha
    k_alpha = alpha(reliability_data, level_of_measurement='nominal')
    
    print(f"Krippendorff's alpha: {k_alpha}")
