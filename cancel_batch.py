#!/usr/bin/env python3

import argparse

import openai


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('batch_id')
    args = parser.parse_args()

    client = openai.Client()
    client.batches.cancel(args.batch_id)
    print('DONE')
