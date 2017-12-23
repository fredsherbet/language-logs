#!/usr/bin/python

import sys
import shlex
from collections import Counter


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
        self.parts = shlex.split(log_line)
        self.parts[3] += ' %s' % self.parts[4]
        del self.parts[4]
        assert self.parts[3].startswith('[')
        assert self.parts[3].endswith(']')

    def __str__(self):
        return "AccessLogLine: " + " ".join(self.parts)

    def __getattr__(self, name):
        try:
            return self.parts[self.NAME_MAP[name]]
        except KeyError:
            raise AttributeError("%s has no %s" % (self, name))

    @property
    def path(self):
        return self.request.split()[1].split('?', 1)[0]

    @property
    def is_successful_request(self):
        return self.status.startswith('2')


def get_report(log_file):
    lang_amounts = {}
    non_ascii_names = []
    total_request_count = 0
    successful_request_count = 0

    apache_regex = '([(\d\.)]+) - - \[([^\]]*)\] "([^"]*)" (\d+) - "(.*?)" "(.*?)"'

    for log_line in log_file.readlines():
        log = ApacheLogLine(log_line)

        non_ascii_file = get_non_ascii_file(log.path)
        total_request_count += 1
        if non_ascii_file:
            non_ascii_names.append(non_ascii_file)
        if not log.is_successful_request:
            continue
        successful_request_count += 1
        try:
            lang_amounts[get_lang(log.path)] += int(log.bytes)
        except KeyError:
            lang_amounts[get_lang(log.path)] = int(log.bytes)

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
    print get_report(sys.stdin)


