#!/usr/bin/env python3
"""
Ansible dynamic inventory backed by Homelab Inventory.

Usage:
    export HOMELAB_INVENTORY_URL=http://homelab-inventory:5000
    chmod +x homelab_inventory.py
    ansible-inventory -i homelab_inventory.py --graph
    ansible -i homelab_inventory.py tag_prod -m ping

Environment:
    HOMELAB_INVENTORY_URL     Base URL of the app (required)
    HOMELAB_INVENTORY_TOKEN   Optional bearer token, sent as Authorization header
    HOMELAB_INVENTORY_FILTER  Optional query string appended to the request,
                              e.g. "tag=prod&monitoring_enabled=true"
    HOMELAB_INVENTORY_TIMEOUT Request timeout in seconds (default 10)
    HOMELAB_INVENTORY_INSECURE Set to 1 to skip TLS verification

Only the Python standard library is used, so it runs anywhere Ansible does.
"""
import argparse
import json
import os
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def fetch(extra_params=None):
    base = os.environ.get('HOMELAB_INVENTORY_URL', '').rstrip('/')
    if not base:
        sys.exit('HOMELAB_INVENTORY_URL is not set')
    query = os.environ.get('HOMELAB_INVENTORY_FILTER', '').lstrip('?&')
    if extra_params:
        query = '&'.join(p for p in (query, urlencode(extra_params)) if p)
    url = f"{base}/api/export/ansible" + (f"?{query}" if query else '')

    req = Request(url, headers={'Accept': 'application/json'})
    token = os.environ.get('HOMELAB_INVENTORY_TOKEN')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    context = None
    if os.environ.get('HOMELAB_INVENTORY_INSECURE') == '1':
        context = ssl._create_unverified_context()  # noqa: S323 - explicit opt-in
    try:
        with urlopen(req, timeout=float(os.environ.get('HOMELAB_INVENTORY_TIMEOUT', '10')), context=context) as resp:  # noqa: S310
            return json.loads(resp.read().decode('utf-8'))
    except HTTPError as exc:
        sys.exit(f'Homelab Inventory returned HTTP {exc.code} for {url}')
    except URLError as exc:
        sys.exit(f'Cannot reach Homelab Inventory at {base}: {exc.reason}')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true', help='List all groups and hosts')
    group.add_argument('--host', help='Show variables for one host')
    args = parser.parse_args()

    data = fetch({'host': args.host} if args.host else None)
    json.dump(data, sys.stdout, indent=2 if sys.stdout.isatty() else None)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
