import json as json_library
import re

class StandardParsers:

    def __init__(self, log):
        self.log = log
    
    def parse(self, parser, blob):
        if parser[0]['name'] == 'json':
            matched_facts = self.json_parse(parser[0], blob)
        elif parser[0]['name'] == 'line':
            matched_facts = self.line(parser[0], blob)
        else:
            matched_facts = self.regex(parser[0], blob)
            
        return matched_facts

    def line_parse(self, parser, blob):
        return [dict(fact=parser['property'], value=f.strip(), set_id=0) for f in blob.split('\n') if f]
    
    def json_parse(self, parser, blob):
        matched_facts = []
        if blob:
            try:
                structured = json_library.loads(blob)
            except:
                self.log.warning('Malformed json returned. Unable to retrieve any facts.')
                return matched_facts
            if isinstance(structured, (list,)):
                for i, entry in enumerate(structured):
                    matched_facts.append((dict(fact=parser['property'], value=entry.get(parser['script']), set_id=i)))
            elif isinstance(structured, (dict,)):
                dict_match = parser['script']
                dict_match = dict_match.split(',')
                match = structured
                for d in dict_match:
                    match = match[d]
                matched_facts.append((dict(fact=parser['property'], value=match, set_id=0)))
            else:
                matched_facts.append((dict(fact=parser['property'], value=structured[parser['script']], set_id=0)))
        return matched_facts
    
    
    def regex_parse(self, parser, blob):
        matched_facts = []
        for i, v in enumerate([m for m in re.findall(parser['script'], blob.strip())]):
            matched_facts.append(dict(fact=parser['property'], value=v, set_id=i))
        return matched_facts