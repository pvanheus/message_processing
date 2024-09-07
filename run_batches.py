#!/usr/bin/env python3

import argparse
import csv
import datetime
import re
import shlex
import subprocess
import sys
import time

from typing import TextIO

from sqlmodel import Session, create_engine, select, and_, func

from batch_models import Job, StateEnum
from message_models import Message
from check_for_spam import load_spam_file, count_messages

# def count_messages(db_path: str, year: int, month: int, start_day: int, end_day: int) -> int:
#     engine = create_engine(f"sqlite:///{db_path}")
#     with Session(engine) as session:
#         query = select(func.count(Message.id)).where(and_(Message.year == year, Message.month == month,
#                                            Message.day >= start_day, Message.day <= end_day))
#         message_count = session.exec(query).one()
#         return message_count
# 
# 
def run_job(year: int, month: int, start_day: int, end_day: int, results_filename: str, session: Session,
            spam_messages_file: str, start_message_num: int = 0, batch_size: int = 1000000) -> Job:
    month_name = datetime.date(1900, month, 1).strftime('%B').lower()
    output_prefix = results_filename.split('_')[0] if '_' in results_filename else f'{month_name}{start_day}{year}'
    batch_info_filename = f'{output_prefix}_batchinfo.txt'
    print(f'starting at {start_message_num} with batch size {batch_size}', file=sys.stderr)
    run_cmd_str = f'./load_chatgpt_batch.py --starting_message_num {start_message_num} --batch_size {batch_size} messages.db classify_chat_log_system_msg.txt {spam_messages_file} {year} {month} {start_day} {end_day} {batch_info_filename}'
    run_cmd = shlex.split(run_cmd_str)
    print(run_cmd)
    while True:
        proc = subprocess.run(run_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            if b'billing_hard_limit_reached' in proc.stderr:
                print('Billing hard limit reached, waiting 10 minutes', file=sys.stderr)
                time.sleep(600)
                continue
            print('Job failed', proc.stderr)
            sys.exit(1)
        else:
            print('Job started', proc.stderr)
            break
    batch_id_re = re.compile(r"Batch\(id='([^']*)'")
    batch_id_match = batch_id_re.match(open(batch_info_filename).read())
    if batch_id_match is None:
        print('Job failed', 'No batch id found')
        sys.exit(1)
    batch_id = batch_id_match.group(1)
    job = Job(id=batch_id, status=StateEnum.in_progress, year=year, month=month, start_day=start_day, end_day=end_day,
              results_file=results_filename, start_message_num=start_message_num, end_message_num=start_message_num + batch_size)
    session.add(job)
    session.commit()
    return job

    
def wait_for_job(job: Job, session: Session):
    failed_messages_filename = job.results_file.replace('.csv', '_failed_messages.txt')
    check_cmd_str = f'./check_batch_status.py --failed_messages_file {failed_messages_filename} {job.id} {job.results_file}'
    check_cmd = shlex.split(check_cmd_str)
    while True:
        proc = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print('Checking on job failed: cmd:', check_cmd_str, '\nstderr:', proc.stderr, '\nstdout:', proc.stdout)
            sys.exit(1)
        if proc.stdout.startswith(b'Batch'):
            if b"'failed'" in proc.stdout:
                job.status = StateEnum.failed
                job.log_message = proc.stdout
                session.add(job)
                session.commit()
                print('Job failed', job, proc.stdout)
                sys.exit(1)
            time.sleep(60)
        elif proc.stderr.startswith(b'DONE'):
            job.status=StateEnum.completed
            session.add(job)
            session.commit()
            break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch_size', type=int, default=1000)
    parser.add_argument('db_path', help='Path to the database file')
    parser.add_argument('job_spec_file', type=argparse.FileType(), help='Path to the job spec file')
    parser.add_argument('message_db_path', help='Path to the message database file')
    parser.add_argument('spam_message_file', type=argparse.FileType(), help='File of spammy messages to exclude from analysis')
    args = parser.parse_args()


    engine = create_engine(f"sqlite:///{args.db_path}")
    message_db_name = 'messages.db'
    spec_reader = csv.DictReader(args.job_spec_file)

    spammy_messages = load_spam_file(args.spam_message_file)

    while True:
        query = select(Job).where(Job.status == StateEnum.in_progress)
        with Session(engine) as session:
            job = session.exec(query).first()
            if job is None:
                # no in_progress jobs, look for completed and unstarted jobs
                for row in spec_reader:
                    query = (select(Job).
                             where(and_(Job.year == row['year'], Job.month == row['month'],
                                        Job.start_day == row['start_day'], Job.end_day == row['end_day'])).
                                order_by(Job.end_message_num.desc()))
                    message_count = count_messages(args.message_db_path, spammy_messages, int(row['year']), int(row['month']),
                                                    int(row['start_day']), int(row['end_day']))[0]
                    job = session.exec(query).first()
                    if job is None or (job.status == StateEnum.completed and job.end_message_num < message_count):
                        cont_text = f'continuing from {job.end_message_num}' if job is not None else ''
                        print('running job for', row, cont_text)

                        for start in range(0, message_count, args.batch_size):
                            end = min(start + args.batch_size, message_count)
                            query = select(Job).where(and_(Job.year == row['year'], Job.month == row['month'],
                                                Job.start_day == row['start_day'], Job.end_day == row['end_day'],
                                                Job.start_message_num == start, Job.end_message_num == end))
                            job = session.exec(query).first()
                            if job is not None:
                                # skip completed jobs
                                continue
                            results_file = f"{row['year']}_{row['month']}_{row['start_day']}_{row['end_day']}_{start}_{end}.csv"
                            job = run_job(int(row['year']), int(row['month']),
                                        int(row['start_day']), int(row['end_day']),
                                        results_file, session, args.spam_message_file.name, start, args.batch_size)
                            wait_for_job(job, session)
                        # job = run_job(int(row['year']), int(row['month']),
                        #         int(row['start_day']), int(row['end_day']),
                        #         row['results_file'], session)
                        # wait_for_job(job, session)
                        continue            
                    elif job.status == StateEnum.completed:
                        # skip completed jobs
                        continue
                else:
                    print('no jobs to run')
                    break

            else:
                print('waiting on job', job)
                wait_for_job(job, session)
            continue