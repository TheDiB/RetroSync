#!/usr/bin/env python3
"""RetroSync: read-only inventory, decisions, and sync planning, v0.4."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from decision import baseline_hash, decide, load_baseline
from planner import plan_sram
from preflight import preflight, check_exit_code
from terminal_colors import colorize_status, use_color


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def check_mount(mount, expected_source):
    p = subprocess.run(['findmnt', '-n', '-M', str(mount), '-o', 'SOURCE,FSTYPE'],
                       capture_output=True, text=True, timeout=5)
    if p.returncode != 0:
        raise RuntimeError(f'NAS not mounted at {mount}')
    parts = p.stdout.strip().split()
    if parts != [expected_source, 'cifs']:
        raise RuntimeError(f'Unexpected NAS mount: {parts!r}')


def classify(name, base):
    if name == base + '.srm':
        return 'SRAM'
    suffix = name.removeprefix(base + '.state')
    if name.startswith(base + '.state') and (suffix == '' or suffix.isdigit()):
        return 'STATE'
    return None


def inventory(folder, base):
    if not folder.is_dir():
        raise RuntimeError(f'Directory missing or inaccessible: {folder}')
    out = {}
    for p in folder.iterdir():
        kind = classify(p.name, base)
        if not kind or not p.is_file():
            continue
        st = p.stat()
        out[p.name] = {'type': kind, 'bytes': st.st_size,
                       'mtime_utc': datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                       'sha256': digest(p)}
    return out


def main():
    parser = argparse.ArgumentParser(description='RetroSync read-only inventory and decisions')
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    parser.add_argument('--json', action='store_true', help='Print machine-readable JSON')
    parser.add_argument('--baseline', type=Path, help='Trusted last-synced SRAM hashes (read only)')
    parser.add_argument('--check', action='store_true', help='Run read-only environment preflight checks')
    parser.add_argument('--color', choices=('auto', 'always', 'never'), default='auto',
                        help='Colorize terminal status labels (default: auto)')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    if config.get('schema_version') != 1:
        raise RuntimeError('Unsupported config schema')
    if args.check:
        checks = preflight(config, check_mount)
        if args.json:
            print(json.dumps({'checks': checks}, indent=2, ensure_ascii=False))
        else:
            print('RetroSync v0.4 | PREFLIGHT | READ ONLY')
            enabled = use_color(args.color, sys.stdout)
            for check in checks:
                label = colorize_status(check['status'], enabled)
                print(f"{label} {check['name']}: {check['detail']}")
        return check_exit_code(checks)
    baselines = load_baseline(args.baseline, config['device_id'])
    nas = config['nas']
    mount = Path(nas['mount'])
    check_mount(mount, nas['expected_source'])
    root = mount / nas['remote_root']
    report = {'device_id': config['device_id'], 'baseline': str(args.baseline) if args.baseline else None, 'games': []}
    for game in config['games']:
        local = Path(game['local_dir'])
        remote = root / game['remote_dir']
        left = inventory(local, game['filename'])
        right = inventory(remote, game['filename'])
        srm = game['filename'] + '.srm'
        status = ('MISSING' if srm not in left or srm not in right else
                  'IDENTICAL' if left[srm]['sha256'] == right[srm]['sha256'] else 'DIFFERENT')
        local_sha = left.get(srm, {}).get('sha256')
        remote_sha = right.get(srm, {}).get('sha256')
        reference_sha = baseline_hash(baselines, game['id'])
        decision = decide(local_sha, remote_sha, reference_sha)
        plan = plan_sram(local / srm, remote / srm, local_sha, remote_sha, reference_sha)
        report['games'].append({'id': game['id'], 'local': left, 'remote': right,
                                'sram_status': status, 'sram_decision': decision,
                                'baseline_sha256': reference_sha, 'sram_plan': plan})
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"RetroSync v0.4 | device: {report['device_id']} | READ ONLY")
        print(f"Baseline: {report['baseline'] or 'NONE'}")
        for game in report['games']:
            print(f"\n{game['id']} | SRAM decision: {game['sram_decision']} ({game['sram_status']})")
            plan = game['sram_plan']
            print(f"  Plan: {plan['operation']} | {plan['reason']}")
            if plan['operation'] == 'COPY_PROPOSED':
                print(f"    from: {plan['source']}")
                print(f"    to:   {plan['destination']}")
            for side in ('local', 'remote'):
                entries = game[side]
                print(f"  {side}: {len(entries)} files")
                for name, item in sorted(entries.items(), key=lambda x: x[1]['mtime_utc'], reverse=True):
                    print(f"    {name}: {item['type']} {item['bytes']} B sha256={item['sha256'][:16]}")
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(2)
