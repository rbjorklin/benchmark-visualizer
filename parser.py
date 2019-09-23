#!/usr/local/bin/python3
# vim: set softtabstop=4 tabstop=4 shiftwidth=4 expandtab autoindent smartindent syntax=python:

import pandas
import argparse
import psycopg2

class RequestStatistics:
    def __init__(self, path, timestamp, min, mean, median, std, q25, q75, q90, q95, q99, q999, max, throughput, successful, failed):
        self.path = path
        self.timestamp = int(timestamp)
        self.min = int(min)
        self.median = float(median)
        self.mean = round(mean, 2)
        self.std = round(std, 2)
        self.q25 = round(q25, 2)
        self.q75 = round(q75, 2)
        self.q90 = round(q90, 2)
        self.q95 = round(q95, 2)
        self.q99 = round(q99, 2)
        self.q999 = round(q999, 2)
        self.max = int(max)
        self.throughput = float(throughput)
        self.successful = int(successful)
        self.failed = int(failed)

class HistStat:
    def __init__(self, path, timestamp, count, label, milliseconds):
        self.path = path
        self.timestamp = int(timestamp)
        self.count = int(count)
        self.label = label
        self.milliseconds = int(milliseconds)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '-ho',
            '--host',
            type=str,
            default="postgres",
            help='Database host')
    parser.add_argument(
            '-po',
            '--port',
            type=str,
            default="5432",
            help='Database port')
    parser.add_argument(
            '-d',
            '--database',
            type=str,
            default="benchmarks",
            help='Database to use')
    parser.add_argument(
            '-a',
            '--application',
            type=str,
            default="example",
            help='Application to publish results for. (stored in separate tables)')
    parser.add_argument(
            '-f',
            '--file',
            type=str,
            default="results.csv",
            help='results.csv file from JMeter to read')
    parser.add_argument(
            '-u',
            '--user',
            type=str,
            help='Database user')
    parser.add_argument(
            '-pa',
            '--password',
            type=str,
            help='Database password')
    parser.add_argument(
            '-c',
            '--commit',
            type=str,
            help='Commit hash to tag results with')
    parser.add_argument(
            '-b',
            '--bins',
            type=int,
            default="10",
            help='The number of bins to split values into')
    args = parser.parse_args()

    df = pandas.read_csv(args.file,
            usecols=['timeStamp', 'elapsed', 'label', 'bytes', 'sentBytes', 'success'])

    first_timestamp = int(df.timeStamp[0])
    last_timestamp = int(df.timeStamp[df.timeStamp.last_valid_index()])

    labels = df.label.unique()

    results_by_label = df.groupby('label')
    request_path_statistics = []
    request_path_hist = []

    for label in labels:
        request_path_statistics.append(RequestStatistics(
            label,
            first_timestamp,
            results_by_label.elapsed.get_group(label).min(),
            results_by_label.elapsed.get_group(label).mean(),
            results_by_label.elapsed.get_group(label).median(),
            results_by_label.elapsed.get_group(label).std(),
            results_by_label.elapsed.get_group(label).quantile(0.25),
            results_by_label.elapsed.get_group(label).quantile(0.75),
            results_by_label.elapsed.get_group(label).quantile(0.90),
            results_by_label.elapsed.get_group(label).quantile(0.95),
            results_by_label.elapsed.get_group(label).quantile(0.99),
            results_by_label.elapsed.get_group(label).quantile(0.999),
            results_by_label.elapsed.get_group(label).max(),
            results_by_label.elapsed.get_group(label).count() / ((last_timestamp - first_timestamp) /1000),
            results_by_label.success.get_group(label).value_counts().get(True, 0),
            results_by_label.success.get_group(label).value_counts().get(False, 0)
            ))

        label_series = results_by_label.elapsed.get_group(label)
        label_bins = pandas.cut(label_series.values, bins=args.bins, precision=0)
        for key, count in label_bins.value_counts().to_dict().items():
            request_path_hist.append(HistStat(
                label,
                first_timestamp / 1000,
                count,
                str(int(key.right)) + 'ms',
                int(key.right)
                ))

    conn = psycopg2.connect(host=args.host, port=args.port,
            dbname=args.database, user=args.user, password=args.password)
    cur = conn.cursor()

    # heatmap table
    #cur.execute("CREATE TABLE IF NOT EXISTS {} (id SERIAL PRIMARY KEY, commit VARCHAR(40), timestamp BIGINT,\
    #        bucket INTEGER, label INTEGER, path TEXT);".format(args.application + '_heat'))

    cur.execute("CREATE TABLE IF NOT EXISTS {} (id SERIAL PRIMARY KEY, commit VARCHAR(40), timestamp BIGINT,\
            count INTEGER, milliseconds INTEGER, label TEXT, path TEXT);".format(args.application + '_hist'))

    cur.execute("CREATE TABLE IF NOT EXISTS {} (id SERIAL PRIMARY KEY, commit VARCHAR(40), timestamp BIGINT,\
            successful INTEGER, failed INTEGER, min INTEGER, median INTEGER, max INTEGER,\
            mean REAL, q25 REAL, q75 REAL, q90 REAL, q95 REAL,\
            q99 REAL, q999 REAL, std_dev REAL, throughput REAL,\
            path TEXT, UNIQUE (commit, path));".format(args.application))

    for r in request_path_statistics:
        cur.execute("INSERT INTO {} (commit, timestamp, successful, failed, min, median, max,\
        mean, q25, q75, q90, q95, q99, q999, std_dev, throughput,\
            path) VALUES\
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);".format(args.application),
            (args.commit, r.timestamp, r.successful, r.failed, r.min, r.median, r.max, r.mean, r.q25, r.q75,
            r.q90, r.q95, r.q99, r.q999, r.std, r.throughput, r.path))

    for r in request_path_hist:
        cur.execute("INSERT INTO {} (commit, timestamp, count, milliseconds, label, path) VALUES\
            (%s, %s, %s, %s, %s, %s);".format(args.application + '_hist'),
            (args.commit, r.timestamp, r.count, r.milliseconds, r.label, r.path))

    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
