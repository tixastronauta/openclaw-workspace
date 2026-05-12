import json, subprocess, urllib.request, re, time, random
from pathlib import Path

SHEET='1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E'
TAB='dges_cursos_2026'
ACCOUNT='tiago.carvalho@gmail.com'
START_ROW=200
BATCH_SIZE=20
SLEEP_MIN=8
SLEEP_MAX=18
LOG=Path('/data/.openclaw/workspace/process_dges_notes.log')


def sh(cmd):
    return subprocess.check_output(cmd, text=True)


def get_range(rng):
    return json.loads(sh(['gog','sheets','get',SHEET,rng,'--account',ACCOUNT,'--json','--no-input']))


def update_range(rng, values):
    subprocess.run(['gog','sheets','update',SHEET,rng,'--account',ACCOUNT,'--values-json',json.dumps(values),'--input','USER_ENTERED','--no-input'], check=True)


def meta():
    return json.loads(sh(['gog','sheets','metadata',SHEET,'--account',ACCOUNT,'--json','--no-input']))


def log(msg):
    with LOG.open('a', encoding='utf-8') as f:
        f.write(msg + '\n')


def extract_vals(url):
    if not url:
        return ['']*6
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        html=r.read().decode('latin-1','ignore')
    m=re.search(r'Nota de Candidatura do Último Colocado pelo Contingente Geral</th>(.*?)</tr>', html, re.S|re.I)
    if not m:
        return ['']*6
    cells=re.findall(r'<td[^>]*>(.*?)</td>', m.group(1), re.S|re.I)
    vals=[]
    for c in cells[:6]:
        c=re.sub(r'<[^>]+>','',c)
        c=c.replace('&nbsp;',' ').replace('\xa0',' ').strip()
        vals.append(c.replace(',','.') if re.fullmatch(r'\d{2,3},\d|\d{2,3}\.\d', c) else '')
    while len(vals)<6:
        vals.append('')
    return vals


def row_has_existing(row):
    return any(cell.strip() for cell in row if isinstance(cell, str))


def main():
    row_count=meta()['sheets'][0]['properties']['gridProperties']['rowCount']
    current=START_ROW
    log(f'resuming from row {START_ROW}')
    while current <= row_count:
        batch_end=min(current+BATCH_SIZE-1, row_count)
        base=get_range(f'{TAB}!A{current}:N{batch_end}').get('values', [])
        out=[]
        target_rows=[]
        for idx in range(current, batch_end+1):
            rel=idx-current
            row=base[rel] if rel < len(base) else []
            existing=row[8:14] if len(row) >= 14 else []
            if row_has_existing(existing):
                out.append(existing + ['SKIP'])
                continue
            url=row[7] if len(row)>7 else ''
            try:
                extracted=extract_vals(url)
                log(f'row {idx} ok {extracted}')
            except Exception as e:
                extracted=['']*6
                log(f'row {idx} error {e}')
            out.append(extracted + ['DO'])
            time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
        # compress contiguous write payload preserving rows; write whole block with old/new values
        write=[]
        for row in out:
            vals=row[:6] if row[-1]=='DO' else row[:6]
            write.append(vals)
        update_range(f'{TAB}!I{current}:N{batch_end}', write)
        log(f'updated rows {current}-{batch_end}')
        current=batch_end+1
        time.sleep(random.uniform(20,40))
    log('completed')


if __name__ == '__main__':
    main()
