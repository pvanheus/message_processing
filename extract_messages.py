#!/usr/bin/env python3

# Extract messages from a database and output them in an Excel file,
# ready for manual review and categorization.

import argparse
import csv
import sys

from datetime import datetime
from typing import TextIO

from sqlmodel import select, Session

import xlsxwriter

from message_models import activate_db, Message, Link

def gather_messages(db_path: str, start_date: str, end_date: str, min_words: int):
    """
    Gather messages from the database within the specified date range and with a minimum word count.
    Args:
        db_path (str): Path to the SQLite database file.
        start_date (str): Start date for filtering messages in 'YYYY-MM-DD' format.
        end_date (str): End date for filtering messages in 'YYYY-MM-DD' format.
        min_words (int): Minimum number of words a message must contain to be included.
    """

    start_timestamp = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
    end_timestamp = datetime.strptime(end_date, "%Y-%m-%d").timestamp()

    engine = activate_db(db_path)
    
    with Session(engine) as session:
        query = select(Message).where(
            (Message.reply_to_message_id == None) &  # Only top-level messages
            (Message.text != '') &
            (Message.date_unixtime >= start_timestamp) & 
            (Message.date_unixtime <= end_timestamp)
        )

        messages = session.exec(query).all()
        filtered_messages = []
        for message in messages:
            text = message.text.strip()
            if len(text) < min_words:
                continue
            filtered_messages.append(message)
    return filtered_messages


def write_results(output_filename, messages):
    """
    Write the results to an Excel file.
    """
    workbook = xlsxwriter.Workbook(output_filename)
    worksheet = workbook.add_worksheet('Messsages')
    bold_format = workbook.add_format({'bold': True})
    # Create a validation sheet for themes
    validation_sheet = workbook.add_worksheet('Validation')
    themes = [
        'adv.impacts',
        'access.info',
        'conspiracy',
        'alt.remedies',
        'vaccine.comp',
        'misinfo',
        'community',
        'other'
    ]
    validation_sheet.write('A1', 'Themes', bold_format)
    for row_number, theme in enumerate(themes, start=1):
        validation_sheet.write(row_number, 0, theme)

    # Write headers
    headers = ['id', 'date', 'text', 'theme']
    worksheet.write_row(0, 0, headers, bold_format)
    worksheet.data_validation('D2:D1000', {
        'validate': 'list',
        'source': '=Validation!$A$1:$A$8',
        'input_message': 'Select a theme from the list',
        'error_message': 'Invalid theme selected'
    }) # type: ignore

    text_wrap_format = workbook.add_format({'text_wrap': True})
    worksheet.set_column(1, 1, 18)  # date
    worksheet.set_column(2, 2, 50)  # text
    message_count = 0
    # Write data
    for row_num, message in enumerate(messages, start=1):
        worksheet.write(row_num, 0, message.id)
        worksheet.write(row_num, 1, message.date)
        worksheet.write(row_num, 2, message.text.strip(), text_wrap_format)
        message_count += 1
    workbook.close()

    return message_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract messages from a database and output them in a specific format.")
    parser.add_argument("--min_words", type=int, default=3, help="Minimum number of words in a message to be included in the output.")
    parser.add_argument("--start_date", type=str, default='2021-05-10', help="Start date for filtering messages (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default='2022-05-17', help="End date for filtering messages (YYYY-MM-DD).")
    parser.add_argument("db_path", type=str, help="Path to the SQLite database file.")
    parser.add_argument("output_file", type=str, help="Output file for extracted messages.")
    args = parser.parse_args()

    filtered_messages = gather_messages(args.db_path, args.start_date, args.end_date, args.min_words)
    message_count = write_results(args.output_file, filtered_messages)
    print("Extracted {} messages to {}".format(message_count, args.output_file))