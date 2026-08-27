#!/usr/bin/env python3
"""배포된 사이트맵을 읽어 IndexNow 참여 검색엔진에 갱신 URL 을 통보한다.

참여 엔진은 Bing·Naver·Yandex·Seznam·Yep 이다. Google 은 참여하지 않으므로
이 경로로는 구글 색인이 열리지 않는다.

기본은 최근 갱신분만 보낸다. 전량을 매 배포마다 보내면 변경 없는 URL 이 반복
제출되고, 제출 자체가 갱신 신호로서 의미를 잃는다. 기존 글을 처음 한 번 올릴
때는 INDEXNOW_ALL=true 로 실행한다.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

HOST = "blog.idean.me"
SITEMAP_URL = f"https://{HOST}/sitemap.xml"
ENDPOINT = "https://api.indexnow.org/IndexNow"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
WINDOW_DAYS = 7
TIMEOUT_SECONDS = 30


def parse_urls(xml, cutoff):
    """cutoff 를 주면 lastmod 가 그 이후인 URL 만, None 이면 전부 돌려준다."""
    root = ElementTree.fromstring(xml)
    picked = []
    for entry in root.findall("sm:url", SITEMAP_NS):
        loc = entry.findtext("sm:loc", namespaces=SITEMAP_NS)
        if not loc:
            continue
        if cutoff is None:
            picked.append(loc)
            continue
        lastmod = entry.findtext("sm:lastmod", namespaces=SITEMAP_NS)
        if not lastmod:
            continue
        try:
            stamp = datetime.fromisoformat(lastmod)
        except ValueError:
            print(f"lastmod 를 읽지 못해 건너뛴다: {loc} ({lastmod})", file=sys.stderr)
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if stamp >= cutoff:
            picked.append(loc)
    return picked


def submit(urls, key):
    payload = json.dumps(
        {
            "host": HOST,
            "key": key,
            "keyLocation": f"https://{HOST}/{key}.txt",
            "urlList": urls,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.status


def main():
    key = os.environ.get("INDEXNOW_KEY", "").strip()
    if not key:
        print("INDEXNOW_KEY 가 비어 있다", file=sys.stderr)
        return 1

    submit_all = os.environ.get("INDEXNOW_ALL", "").strip().lower() == "true"
    cutoff = None if submit_all else datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)

    with urllib.request.urlopen(SITEMAP_URL, timeout=TIMEOUT_SECONDS) as response:
        xml = response.read()

    urls = parse_urls(xml, cutoff)
    if not urls:
        print(f"최근 {WINDOW_DAYS}일 갱신 URL 없음. 통보를 생략한다")
        return 0

    scope = "전량" if submit_all else f"최근 {WINDOW_DAYS}일"
    try:
        status = submit(urls, key)
    except urllib.error.HTTPError as error:
        print(f"통보 실패: HTTP {error.code} {error.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return 1

    print(f"{scope} {len(urls)}건 통보. HTTP {status}")
    for url in urls:
        print(f"  {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
