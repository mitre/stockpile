from basic_filter_out import Parser as BasicFilterOutParser


FILTER_OUT_REGEXS = [
  "Permission denied"
]


class Parser(BasicFilterOutParser):
    """Parser for removing 'Permission Denied' messages from 'find' command output"""
    def __init__(self, parser_info):
        super().__init__(parser_info, regexs=FILTER_OUT_REGEXS)
