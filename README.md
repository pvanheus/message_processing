### Message processing code

The SQLite3 model is done using SQLModel, migrations are done using Alembic.

Dependencies:
* SQLModel and SQLAlchemy - used for all the database interactions
* tqdm - used for progress bars
* altair - used for drawing graphs
* requests - used to resolve links
* openai - OpenAI API interface

The `message_models.py` contains the Message and Link models and is used by all other code.

`store_messages.py` reads in the JSON dump from Telegram and populates the DB.

`batch_models.py` contains the Job model and StateEnum enum that is used for keeping track of jobs submitted to the OpenAI batch API

To identify and deal with spam, `find_spammy_messages.py` looks for identical messages that occur many times in the database and
`check_for_spam.py` has some routimes for loading the spam messages file. As a command line script it can provide statitics, as a module it is widely used to provide a set of spam messages to filter out.

`load_chatgpt_batch.py` loads a batch of messages along with a prompt into the OpenAI batch API for ChatGPT. An API key must be provided using the `OPENAI_API_KEY` environment variable. The `run_batches.py` reads a job specification file (e.g. `job_specs.csv`),
checkes if the batch has been processed and either starts a new batch or waits on the results being available (using `check_batch_status.py`). `cancel_batch.py` can be used to cancel a batch job in the OpenAI API. `gather_results.py` reads the job outputs (as listed in the jobs database) and summarises results.

The `anonymize_from_id.py` script adds anonymous IDs so that the real Telegram user IDs don't need to be used in the analysis.

`find_user_flows.py` collects statistics on users that do most of the posting to the group and how the top users have changed or stayed the same over time. `count_user_ids.py` is used to count the monthly users posting to the group.

`plot_results.ipynb` creates the plots used in the paper.

`prepare_messages_for_publication.py` consolidates all the messages that have been processed and ensures that no known spam is included and ensures that user IDs are anonymous.

These scripts are historic and were not used in the final analysis:

`thread_stats.py` computes some statistics on the threads (i.e. chains of replies) in the messages

`resolve_links.py` looks up links and resolves them (using requests) to get a "canonical form" of each link

`visualise.ipynb` has some early experiments in visualisation of the data

