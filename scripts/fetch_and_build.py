import requests
import chardet
import json
import re
import sys
from datetime import datetime

# ── 다운로드 URL 목록 (최신순) ──────────────────────────────
# 새 분기 파일이 올라오면 여기에 맨 위에 추가하세요
DOWNLOAD_URLS = [
    "https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003585540&fileDetailSn=1",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.data.go.kr/",
}

def classify(name):
    n = str(name)
    if re.search(r'선박|조선', n): return '조선·선박'
    if re.search(r'자동차|차량', n): return '자동차부품'
    if re.search(r'금속|철강|절삭|도금|볼트|강관|금형|주형|구조용 금속|육상 금속', n): return '금속·철강가공'
    if re.search(r'기계|유압|펌프|밸브|탭', n): return '기계·장비'
    if re.search(r'전기|배전|전자|반도체|통신', n): return '전기·전자'
    if re.search(r'플라스틱|고무', n): return '플라스틱·고무'
    if re.search(r'식품|음식|빵|수산|농산|음료|주류', n): return '식품·수산'
    if re.search(r'섬유|의류|봉제|직물|편조|어망', n): return '섬유·의류'
    if re.search(r'화학|도료|세제|치약|비누|페인트', n): return '화학·도료'
    if re.search(r'가구|목재', n): return '가구·목재'
    if re.search(r'인쇄|출판', n): return '인쇄·출판'
    if re.search(r'의료|의약', n): return '의료·의약'
    return '기타'

def parse_csv(content_bytes):
    detected = chardet.detect(content_bytes)
    encoding = detected.get('encoding', 'euc-kr') or 'euc-kr'
    if encoding.lower() in ('ascii', 'iso-8859-1'):
        encoding = 'euc-kr'
    try:
        text = content_bytes.decode(encoding)
    except:
        text = content_bytes.decode('euc-kr', errors='replace')

    lines = text.splitlines()
    if not lines:
        raise ValueError("빈 파일입니다")

    header = [h.strip().strip('"') for h in lines[0].split(',')]
    print(f"컬럼: {header}")

    rows = []
    for line in lines[1:]:
        parts = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)
        parts = [p.strip().strip('"') for p in parts]
        if len(parts) < 4:
            continue
        try:
            addr = parts[2] if len(parts) > 2 else ''
            m = re.search(r'부산광역시\s+(\S+구|\S+군)', addr)
            biz = re.sub(r'\s*외\s*\d+종', '', parts[3] if len(parts) > 3 else '').strip()
            name = parts[1].strip()
            if not name:
                continue
            rows.append({
                'n': name,
                'a': m.group(1) if m else '기타',
                'c': classify(biz),
                'b': biz
            })
        except:
            continue

    return rows

def main():
    csv_bytes = None
    used_url = None

    for url in DOWNLOAD_URLS:
        try:
            print(f"다운로드 시도: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 1000:
                csv_bytes = resp.content
                used_url = url
                print(f"✓ 다운로드 성공 ({len(csv_bytes):,} bytes)")
                break
            else:
                print(f"✗ 실패 (status={resp.status_code})")
        except Exception as e:
            print(f"✗ 오류: {e}")

    if csv_bytes is None:
        print("모든 URL 다운로드 실패 — 기존 data.js 유지")
        sys.exit(0)

    rows = parse_csv(csv_bytes)
    print(f"파싱 완료: {len(rows):,}개 업체")

    date_label = datetime.now().strftime('%Y년 %m월 기준')
    date_match = re.search(r'(\d{8})', used_url)
    if date_match:
        d = date_match.group(1)
        date_label = f"{d[0:4]}년 {d[4:6]}월 {d[6:8]}일 기준"

    data_js = f"""// 자동 생성 파일 — 수동 수정 금지
// 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)
const DATA_DATE = "{date_label}";
const FACTORY_DATA = {json.dumps(rows, ensure_ascii=False, separators=(',', ':'))};
"""

    with open('data.js', 'w', encoding='utf-8') as f:
        f.write(data_js)

    print(f"✓ data.js 생성 완료 ({len(rows):,}개 업체)")

if __name__ == '__main__':
    main()
