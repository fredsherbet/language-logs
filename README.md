# Language log parser

(Python coding exercise solution, written by Matthew Russell, in December 2017.)

Parses Apache HTTP logs, and produces a monthly report, with the following detail.

1. A sorted list of the top 5 languages, measured by GB of data served from requests for files of that language for that month, including how many GB were served for each language
2. The percentage of requests that were successful (2xx return code) that month
3. A list of all requested filenames that contained non-Ascii characters that month

## Usage

By default, `report.py` reads from stdin, and prints to stdout. You can specify a specific HTTP log file or folder containing HTTP logs, using the options, as shown below.

    usage: report.py [-h] [-i INPUT] [-f FOLDER]

    Produce monthly reports for language server from its Apache HTTP logs

    optional arguments:
      -h, --help            show this help message and exit
      -i INPUT, --input INPUT
                            Apache HTTP log to parse
      -f FOLDER, --folder FOLDER
                            Folder of Apache HTTP log to parse

For example, to produce a report for the logs in `/var/log/apache/access/`, and save the report to `languge-report.txt`, run the following.

    ./report.py -f /var/log/apache/access | tee language-report.txt

## Debugging

The script produces a debugging log, `engineering.log`, which contains some
logging, including details for any exceptions hit or raised.

The exception `LogInputError` indicates a formatting error in the HTTP log.

## Assumptions

The following are assumptions made, for future reference.

* The logs are in chronological order - that allows us to free the details
  about the month when we roll around to the next one, rather than storing all
  details in memory until we've completed parsing all the logs.
