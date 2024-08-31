#!/usr/bin/env python3

import csv
from pathlib import Path

from sqlmodel import create_engine, SQLModel, Session

from batch_models import Job, StateEnum


db_name = 'jobs.db'
engine = create_engine(f"sqlite:///{db_name}")
SQLModel.metadata.create_all(engine)

jobspec_reader = csv.DictReader(open('job_specs.csv'))

with Session(engine) as session:
    for row in jobspec_reader:
        result_path = Path(row['results_file'])
        month = int(row['month'])
        start_day = int(row['start_day'])
        end_day = int(row['end_day'])
        year = int(row['year'])

        if result_path.exists():
            if row['year'] == '2021' and row['month'] == '5':
                id = 'batch_4MYdW7Wc8xVJafXA9b2wYUro'
            elif row['month'] == '6':
                id = 'batch_9gEeISLU7dIwyAVMrvf4HBZN'
            elif row['month'] == '7':
                id = 'batch_b9uODm2K5bUFQFG72h8aWTjn'
            job = Job(id=id, year=year, month=month, start_day=start_day, end_day=end_day,
                    status=StateEnum.completed, results_file=row['results_file'])
        elif row['month'] == '8':
            job = Job(id='batch_OSaa9bQJchoYOt6H5FFbAe1q', year=year, month=month, start_day=start_day, end_day=end_day,
                    status=StateEnum.in_progress)
        session.add(job)
    session.commit()