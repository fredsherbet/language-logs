#!/usr/bin/python

import logging
import sys
import argparse
import shlex
from collections import Counter


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
LOG_FILE = "stdout"


class ReportException(Exception):
    """Exception raised within report.py, with a printable error message"""
    def __init__(self, message, log_line=None, exc=None):
        Exception.__init__(self, message)
        self.log_line = log_line
        self.exc = exc


class ApacheLogLine():
    NAME_MAP = {
        'ip': 0,
        'ruser': 1,
        'luser': 2,
        'time': 3,
        'request': 4,
        'status': 5,
        'bytes': 6,
        }

    def __init__(self, log_line):
        # The apache log is made up of parts, separated by spaces.
        # Some parts can be multi-word, and so wrapped in quotes.
        # The shlex.split handles that for us.
        # There's one wrinkle; the timestamp has spaces, and isn't
        # wrapped in quotes (it's wrapped in square brackets instead),
        # so we'll normalise that, here.
        self.log_line = log_line
        self.parts = shlex.split(log_line)
        self.parts[3] += ' %s' % self.parts[4]
        del self.parts[4]
        self.do_consistency_check()

    def __str__(self):
        return "AccessLogLine: " + " ".join(self.parts)

    def __getattr__(self, name):
        try:
            return self.parts[self.NAME_MAP[name]]
        except KeyError:
            raise AttributeError("%s has no %s" % (self, name))

    def do_consistency_check(self):
        """Just some basic checking - we'll rely on exceptions for most
        issues, rather than trying to preempt every possibility"""
        if not (self.parts[3].startswith('[') and self.parts[3].endswith(']')):
            raise ReportException("Malformatted log line; expected this part "
                                  "to be a date: %s" % self.parts[3],
                                  log_line=self.log_line)
        if not len(self.parts) != 7:
            raise ReportException("Malformatted log line; expected 7 parts, "
                                  "but got %d" % len(self.parts),
                                  log_line=self.log_line)

    @property
    def path(self):
        try:
            return self.request.split()[1].split('?', 1)[0]
        except:
            log.warning("Log line has no path. %s" % self.log_line,
                        exc_info=True)
            return ""

    @property
    def is_successful_request(self):
        return self.status.startswith('2')


def get_report(log_file):
    lang_amounts = {}
    non_ascii_names = []
    total_request_count = 0
    successful_request_count = 0

    for log_line in log_file.readlines():
        try:
            log.debug("Handling line %s" % log_line)
            apache_log = ApacheLogLine(log_line)

            non_ascii_file = get_non_ascii_file(apache_log.path)
            total_request_count += 1
            if non_ascii_file:
                non_ascii_names.append(non_ascii_file)
            if not apache_log.is_successful_request:
                continue
            successful_request_count += 1
            try:
                lang_amounts[get_lang(apache_log.path)] += int(apache_log.bytes)
            except KeyError:
                lang_amounts[get_lang(apache_log.path)] = int(apache_log.bytes)
        except ReportException as exc:
            exc.log_line = log_line
            raise
        except Exception as exc:
            logging.exception("Exception handling line: %s" % log_line)
            raise ReportException(exc.message, log_line, exc)

    return format_report(lang_amounts,
                         successful_request_count,
                         total_request_count,
                         non_ascii_names)


def get_non_ascii_file(path):
    filename = path.split('/')[-1]
    try:
        filename.decode('ascii')
    except UnicodeDecodeError:
        return filename


def get_lang(path):
    # Path is expected to be of the following format.
    #   /<language>/<filename>
    # e.g. /English/some_audio_file.wav
    path_parts = path.split('/')
    if len(path_parts) != 3:
        # The path isn't the expected format, so we don't know what the
        # language is.
        return ''
    return path_parts[1]


def format_report(lang_amounts, successful_request_count,
                  total_request_count, non_ascii_names):
    return """
{date} Report
Top 5 Languages:
{lang}

Request Success:
  {succ}

Non-ascii filenames:
  {non-ascii}""".format(**{'lang': format_lang_table(lang_amounts),
                           'date': '2017',
                           'succ': format_success(successful_request_count,
                                                  total_request_count),
                           'non-ascii': "\n  ".join(non_ascii_names)})


def format_lang_table(lang_amounts):
    return "%s" % dict(Counter(lang_amounts).most_common(5))


def format_success(succ, total):
    return "{:>5}%%     ({:d} of {:d})".format(succ * 100 / total,
                                               succ, total)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="Apache log to parse")
    args = parser.parse_args()

    try:
        if args.input:
            with open(args.input) as f:
                print get_report(f)
        else:
            print get_report(sys.stdin)
    except ReportException as exc:
        logging.exception("Error halted execution")
        print exc.message
        sys.exit(1)
    except:
        logging.exception("Error halted execution")
        print "Report failed. See debugging information in %s" % LOG_FILE
        sys.exit(1)


