#!/usr/bin/python

import sys
from collections import Counter


def get_report(log_file):
    lang_amounts = {}
    non_ascii_names = []
    total_request_count = 0
    successful_request_count = 0

    for log_line in log_file.readlines():
        non_ascii_file = get_non_ascii_file(log_line)
        total_request_count += 1
        if non_ascii_file:
            non_ascii_names.append(non_ascii_file)
        if not successful_request(log_line):
            continue
        successful_request_count += 1
        try:
            lang_amounts[get_lang(log_line)] += get_filesize(log_line)
        except KeyError:
            lang_amounts[get_lang(log_line)] = get_filesize(log_line)

    return format_report(lang_amounts,
                         successful_request_count,
                         total_request_count,
                         non_ascii_names)


def format_report(lang_amounts, successful_request_count,
                  total_request_count, non_ascii_names):
    return """
{date} Report
Top 5 Languages:
{lang}

Request Success:
  {succ}

Non-ascii filenames:
  {non-ascii}""".format({'lang': format_lang_table(lang_amounts),
                         'date': '2017',
                         'succ': format_success(successful_request_count,
                                                total_request_count),
                         'non-ascii': "\n  ".join(non_ascii_names)})


def format_long_table(lang_amounts):
    return "%s" % dict(Counter(lang_amounts).most_common(5))


def format_success(succ, total):
    return "{:>5}%%     ({:d} of {:d})".format(succ * 100 / total,
                                               succ, total)


if __name__ == '__main__':
    print get_report(sys.stdin)


