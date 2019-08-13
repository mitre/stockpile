import re

def hostname(blob):
    nbstat = []
    regex = re.compile(r'^\s*([^<\s]+)\s*<00>\s*UNIQUE')
    result = regex.search(blob)
    if result:
        result = result.group(1)
        if result:
            nbstat += [result]
    return nbstat