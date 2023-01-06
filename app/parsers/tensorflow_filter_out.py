from basic_filter_out import Parser as BasicFilterOutParser


FILTER_OUT_REGEXS = [
  "1/1 [==================="
]


class Parser(BasicFilterOutParser):
    """Parser for removing unwanted Tensorflow messages from output"""
    def __init__(self, parser_info):
        super().__init__(parser_info, regexs=FILTER_OUT_REGEXS)
