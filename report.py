#!/usr/bin/python

import logging
import sys
import os
import argparse
import datetime
import shlex
from collections import Counter


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ReportException(Exception):
    """Execution exception"""
    def __init__(self, message, log_line=None, exc=None):
        Exception.__init__(self, message)
        self.log_line = log_line
        self.exc = exc


class LogInputError(ReportException):
    """Error parsing the log; the log is malformatted"""


def main():
    """Handle command line interface - arguments, logging, and error
    reporting"""
    parser = argparse.ArgumentParser(
            description="Produce monthly reports for language server from its "
                        "Apache HTTP logs")
    parser.add_argument("-i", "--input", help="Apache HTTP log to parse")
    parser.add_argument("-f", "--folder", help="Folder of Apache HTTP log to parse")
    args = parser.parse_args()

    LOG_FILE = "engineering.log"
    logging.basicConfig(level=logging.INFO,
                        filename=LOG_FILE,
                        filemode="w")

    try:
        if args.folder:
            print get_full_report(
                    file_paths=sorted(os.path.join(args.folder, f)
                                      for f in os.listdir(args.folder)))
        elif args.input:
            with open(args.input) as f:
                print get_full_report(f)
        else:
            print get_full_report(sys.stdin)
    except LogInputError as exc:
        logging.exception("Failed to parse HTTP log; failed to produce a report.")
        sys.stderr.write("Failed to parse HTTP log; failed to produce a report.")
        sys.stderr.write(exc.message)
        if exc.log_line:
            sys.stderr.write('Error handling log line:\n  ' + exc.log_line)
        sys.stderr.write("If needed, see further debugging information in " + LOG_FILE)
        return 1
    except:
        logging.exception("Error halted execution; failed to produce a report.")
        sys.stderr.write("Error halted execution; failed to produce a report.")
        sys.stderr.write("See debugging information in " + LOG_FILE)
        return 2
    return 0


def get_full_report(log_file=None, file_paths=None):
    def get_files():
        if log_file:
            yield log_file
        if file_paths:
            for p in file_paths:
                with open(p) as f:
                    yield f

    report_str = ''
    report = None
    for f in get_files():
        for log_line in f.readlines():
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
            except Exception:
                logging.exception("Exception handling line: " + log_line)
                raise

    if report is not None:
        report_str += '\n' + str(report)
    return report_str.strip()


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
        non_ascii_file = self.get_non_ascii_file(apache_log.path)
        self.total_request_count += 1
        if non_ascii_file:
            self.non_ascii_names.append(non_ascii_file)
        if not apache_log.is_successful_request:
            return
        self.successful_request_count += 1
        try:
            try:
                self.lang_amounts[self.get_lang(apache_log.path)] += int(apache_log.bytes)
            except KeyError:
                self.lang_amounts[self.get_lang(apache_log.path)] = int(apache_log.bytes)
        except ValueError as exc:
            raise LogInputError("Bytes count in HTTP log is not an integer.",
                                log_line=self.log_line,
                                exc=exc)

    @staticmethod
    def get_non_ascii_file(path):
        filename = path.split('/')[-1]
        try:
            filename.decode('ascii')
        except UnicodeDecodeError:
            return filename

    @staticmethod
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
            raise AttributeError("{} has no {}".format(self, name))
        except IndexError as exc:
            raise LogInputError("Log line is malformatted; does not have the "
                                "expected number of parts",
                                log_line=self.log_line,
                                exc=exc)

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
        raise LogInputError("Could not parse date " + self.time,
                            log_line=self.log_line)

    @property
    def month_year(self):
        return self.datetime.strftime('%B %Y')


if __name__ == '__main__':
    sys.exit(main())
