#!/usr/bin/env python3

import argparse
import calendar
import csv
import sys

from dataclasses import dataclass

from sqlmodel import Session, create_engine, select

from batch_models import Job, StateEnum
from check_for_spam import load_spam_file

@dataclass
class Outputs:
    year: int
    month: int
    theme_count: dict[str, int]
    message_count: int
    days_completed: int
    num_jobs: int
    start_day: int
    end_day: int

def year_month_key(yearmonth: str) -> str:
    year = int(yearmonth[:4])
    month = int(yearmonth[4:])
    return year * 100 + month

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('db_filename', help='SQLite database filename')
    parser.add_argument('spam_message_file', type=argparse.FileType(), help='File of spammy messages to exclude from analysis')
    parser.add_argument('output_file', type=argparse.FileType('w'), nargs='?', default=sys.stdout, help='Output file')
    args = parser.parse_args()

    spammy_messages = load_spam_file(args.spam_message_file)
    outputs: dict[str, Outputs] = {}
    engine = create_engine(f"sqlite:///{args.db_filename}")
    with Session(engine) as session:
        query = select(Job).where(Job.status == StateEnum.completed)
        jobs = session.exec(query).all()
        if not jobs:
            print('No complted jobs found in the database', file=sys.stderr)
            sys.exit(1)

        for job in jobs:
            month_str = '%02d' % job.month
            year_str = '%04d' % job.year
            key = f'{year_str}{month_str}'
            if key not in outputs:
                outputs[key] = Outputs(job.year, job.month, {}, 0, 0, 0, job.start_day, job.end_day)
                num_jobs = 1
                message_count = 0
            else:
                num_jobs = outputs[key].num_jobs + 1
                message_count = outputs[key].message_count
                if job.start_day < outputs[key].start_day:
                    outputs[key].start_day = job.start_day
                if job.end_day > outputs[key].end_day:
                    outputs[key].end_day = job.end_day
            outputs[key].num_jobs = num_jobs

            reader = csv.DictReader(open(job.results_file))
            themes = set(["access.info", "adv.impacts", "alt.remedies", "community", "conspiracy", "misinfo", "other", "vaccine.comp"])
            theme_count = {theme: 0 for theme in themes}
            
            for row in reader:
                if row['message'] in spammy_messages:
                    continue
                message_count +=1 
                if row['theme'] == '':
                    row['theme'] = 'other'
                if row['theme'] not in themes:
                    print(f'Unknown theme {row["theme"]}: {row}', file=sys.stderr)
                    sys.exit(1)
                theme_count[row['theme']] += 1

            for theme in themes:
                outputs[key].theme_count[theme] = outputs[key].theme_count.get(theme, 0) + theme_count[theme]
            outputs[key].message_count = message_count
            outputs[key].days_completed = outputs[key].end_day - outputs[key].start_day + 1
    
    output_writer = csv.writer(args.output_file)
    output_writer.writerow(['Year-Month'] + list(themes) + ['Days Completed', 'Message Count', 'Num Jobs'])
    keys = sorted(outputs.keys(), key=year_month_key)
    for key in keys:
        output = outputs[key]
        output_writer.writerow([f'{output.year}-{output.month:02d}'] +
                                [output.theme_count[theme] for theme in themes] + 
                                [output.days_completed, output.message_count, output.num_jobs])
