# Language log parser

(Python coding exercise solution, written by Matthew Russell, in December 2017.)

## Usage

    usage: report.py [-h] [-i INPUT] [-f FOLDER]

    Produce monthly reports for language server from its Apache HTTP logs

    optional arguments:
      -h, --help            show this help message and exit
      -i INPUT, --input INPUT
                            Apache HTTP log to parse
      -f FOLDER, --folder FOLDER
                            Folder of Apache HTTP log to parse

## Debugging

The script produces a debugging log, `engineering.log`, which contains some
logging, including details for any exceptions hit or raised.

The exception `LogInputError` indicates a formatting error in the HTTP log.

## Assumptions

The following are assumptions made, for future reference.

* The logs are in chronological order - that allows us to free the details
  about the month when we roll around to the next one, rather than storing all
  details in memory until we've completed parsing all the logs.
