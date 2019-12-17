import argparse
import json

import requests

'''
Use this script to generate a layer for attack-navigator
https://github.com/mitre-attack/attack-navigator
'''


def get_abilities(url):
    payload = json.dumps(dict(index='ability'))
    headers = {
        'Content-Type': 'application/json',
        'API_KEY': 'ADMIN123',
    }
    response = requests.request('POST', url=url + '/plugin/chain/full', data=payload, headers=headers)
    return json.loads(response.text)


def get_layer_boilerplate(name, description):
    return {
        'version': '2.2',
        'name': name,
        'description': description,
        'domain': 'mitre-enterprise',
        'techniques': [],
        'legendItems': [],
        'showTacticRowBackground': True,
        'tacticRowBackground': '#205b8f',
        'selectTechniquesAcrossTactics': True,
        'gradient': {
            'colors': [
                '#ffffff',
                '#66ff66'
            ],
            'minValue': 0,
            'maxValue': 1
        }
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--out-file', default='stockpile-techniques.json', help='layer json output path name')
    parser.add_argument('--url', default='http://127.0.0.1:8888', help='url if not default')
    args = parser.parse_args()

    layer = get_layer_boilerplate(name='stockpile', description='stockpile')
    abilities = get_abilities(url=args.url)

    for ability in abilities:
        technique = {
            'techniqueID': ability['technique_id'],
            'score': 1,
            'color': '',
            'comment': '',
            'enabled': True
        }

        layer['techniques'].append(technique)

    with open(args.out_file, 'w') as f:
        f.write(json.dumps(layer, indent=4))

    print('now navigate to http://localhost:4200/ and upload the newly created output file')
