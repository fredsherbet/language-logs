#!/usr/bin/python

import logging
import sys
import argparse
import datetime
import shlex
from collections import Counter


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


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
        self.parts[3] += ' ' + self.parts[4]
        del self.parts[4]
        self.parts[3] = self.parts[3].strip('[]')

    def __str__(self):
        return "AccessLogLine: " + " ".join(self.parts)

    def __getattr__(self, name):
        try:
            return self.parts[self.NAME_MAP[name]]
        except KeyError:
            raise AttributeError("{0} has no {1}".format(self, name))

    @property
    def path(self):
        try:
            return self.request.split()[1].split('?', 1)[0]
        except:
            log.warning("Log line has no path. " + self.log_line,
                        exc_info=True)
            return ""

    @property
    def is_successful_request(self):
        return self.status.startswith('2')

    @property
    def datetime(self):
        formats = ['%d/%m/%Y:%H:%M:%S',
                   '%d/%b/%Y:%H:%M:%S',
                  ]
        for fmt in formats:
            try:
                return datetime.datetime.strptime(self.time.split()[0], fmt)
            except ValueError as exc:
                pass
        raise ReportException("Could not parse date " + self.time,
                              log_line=self.log_line)

    @property
    def month_year(self):
        return self.datetime.strftime('%B %Y')


class Report():
    """Stores data for a report, and formats it"""
    def __init__(self, title):
        log.info("Start new report " + title)
        self.title = title
        self.lang_amounts = {}
        self.non_ascii_names = []
        self.total_request_count = 0
        self.successful_request_count = 0

    def __str__(self):
        return """
{title} Report
Top 5 Languages:
{lang}

Request Success:
  {succ}

Non-ascii filenames:
  {non-ascii}""".format(**{'title': self.title,
                           'lang': self.format_lang_table(),
                           'succ': self.format_success(),
                           'non-ascii': "\n  ".join(self.non_ascii_names)})

    def format_lang_table(self):
        return "  \n".join(
                "{:>7}  {}".format(self.format_bytes(s), l)
                for (l, s) in Counter(self.lang_amounts).most_common(5))

    @staticmethod
    def format_bytes(num_bytes):
        res = float(num_bytes)
        suffix = ['TB', 'GB', 'MB', 'KB', 'B']
        while res >= 1000:
            suffix.pop()
            res = res / 1024
        if res >= 100:
            fmt = "{:.0f}{:>3}"
        else:
            fmt = "{:.1f}{:>3}"
        return fmt.format(res, suffix.pop())

    def format_success(self):
        return "{:.1f}%  ({:d} of {:d})".format(
                float(self.successful_request_count) * 100 / self.total_request_count,
                self.successful_request_count, self.total_request_count)

    def add_log(self, apache_log):
        non_ascii_file = get_non_ascii_file(apache_log.path)
        self.total_request_count += 1
        if non_ascii_file:
            self.non_ascii_names.append(non_ascii_file)
        if not apache_log.is_successful_request:
            return
        self.successful_request_count += 1
        try:
            self.lang_amounts[get_lang(apache_log.path)] += int(apache_log.bytes)
        except KeyError:
            self.lang_amounts[get_lang(apache_log.path)] = int(apache_log.bytes)


def get_full_report(log_file):
    report_str = ''
    report = None
    for log_line in log_file.readlines():
        log.debug("Handling line " + log_line)
        apache_log = ApacheLogLine(log_line)
        if report is None:
            report = Report(apache_log.month_year)
        if apache_log.month_year != report.title:
            log.info("Formatting report " + report.title)
            report_str += '\n' + str(report)
            report = Report(apache_log.month_year)
        try:
            report.add_log(apache_log)
        except ReportException as exc:
            exc.log_line = log_line
            raise
        except Exception as exc:
            logging.exception("Exception handling line: " + log_line)
            raise ReportException(exc.message, log_line, exc)

    if report is not None:
        report_str += '\n' + str(report)
    return report_str.strip()


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


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="Apache log to parse")
    args = parser.parse_args()

    # @TODO by default, send logs to a file
    LOG_FILE = "engineering.log"
    logging.basicConfig(level=logging.INFO,
                        filename=LOG_FILE,
                        filemode="w")

    try:
        if args.input:
            with open(args.input) as f:
                print get_full_report(f)
        else:
            print get_full_report(sys.stdin)
    except ReportException as exc:
        logging.exception("Error halted execution")
        print exc.message
        if exc.log_line:
            print 'Error handling log line:\n  ' + exc.log_line
        sys.exit(1)
    except:
        logging.exception("Error halted execution")
        print "Report failed. See debugging information in " + LOG_FILE
        sys.exit(1)

