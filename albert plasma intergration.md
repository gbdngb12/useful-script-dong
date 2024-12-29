```python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2014 Manuel Schneider

from albert import *

md_iid = '2.3'
md_version = "1.6"
md_name = "Plasma Intergration"
md_description = "Plasma Intergration"
md_license = "BSD-3"
md_url = "https://github.com/"
md_authors = "@dong"

import io
import sys
from typing import List
new_paths = ["/usr/lib/python3.13/site-packages", "/home/dong/.local/lib/python3.13/site-packages"]

# 경로를 순회하며 sys.path에 추가
for path in new_paths:
    if path not in sys.path:
        sys.path.append(path)


import io
import base64
import dbus
from PIL import Image

def dbus_to_python(obj):
    """DBus 자료형을 파이썬 자료형으로 재귀 변환"""
    if isinstance(obj, dbus.String):
        return str(obj)
    elif isinstance(obj, dbus.Boolean):
        return bool(obj)
    elif isinstance(obj, (dbus.Int16, dbus.Int32, dbus.Int64,
                          dbus.UInt16, dbus.UInt32, dbus.UInt64, dbus.Byte)):
        return int(obj)
    elif isinstance(obj, dbus.Double):
        return float(obj)
    elif isinstance(obj, dbus.Array):
        return [dbus_to_python(x) for x in obj]
    elif isinstance(obj, dbus.Dictionary):
        return {str(k): dbus_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, dbus.Struct):
        return tuple(dbus_to_python(x) for x in obj)
    else:
        return obj

class KRunnerResult:
    """
    KRunner 결과를 객체화한 클래스.
    - rid: id (예: '33')
    - text: 결과 텍스트 (예: 'KDE/plasma-browser-integration...')
    - icon_url: data:image/png;base64,... 형태의 아이콘 URL (없으면 None)
    - subtext: 부가 텍스트 (예: 'https://github.com/...')
    - urls: URL 리스트 (예: ['https://github.com/...'])
    """
    def __init__(self, rid, text, icon_url, subtext, urls):
        self.rid = rid
        self.text = text
        self.icon_url = icon_url
        self.subtext = subtext
        self.urls = urls

    def __repr__(self):
        return (f"KRunnerResult(rid={self.rid}, text={self.text}, "
                f"icon_url={'(BASE64 DATA URI)' if self.icon_url else None}, "
                f"subtext={self.subtext}, urls={self.urls})")
        
def run_krunner_action(match_id: str, action_id: str = ""):
    """
    org.kde.krunner1.Run 메서드를 호출하여 KRunner의 특정 항목을 실행합니다.
    
    :param match_id: 실행할 대상의 ID (예: "33")
    :param action_id: 실행할 동작의 ID (예: "open", 기본값은 빈 문자열로 기본 동작 실행)
    """
    try:
        # DBus 세션 버스 연결
        bus = dbus.SessionBus()
        proxy = bus.get_object('org.kde.plasma.browser_integration', '/TabsRunner')
        interface = dbus.Interface(proxy, 'org.kde.krunner1')

        # Run 메서드 호출
        interface.Run(match_id, action_id)
        print(f"Run 호출 성공: match_id={match_id}, action_id={action_id}")
    except dbus.exceptions.DBusException as e:
        print(f"Run 호출 실패: {e}")

def extract_icon_data(icon_data_tuple):
    """
    icon-data 튜플을 받아서 data:image/png;base64,... 형태의 문자열을 생성해 반환.
    에러시 None 반환.
    """
    try:
        width, height, scaleFactor, hasAlpha, bitsPerSample, channels, raw_bytes = icon_data_tuple
        pixel_data = bytes(raw_bytes)
        mode = 'RGBA' if (channels == 4 and hasAlpha) else 'RGB'

        # Pillow에서 raw 포맷 처리
        # 색상이 이상하면 'raw', 'BGRA' 등으로 바꿔볼 수 있음.
        image = Image.frombytes(mode, (width, height), pixel_data, 'raw', mode)

        # 메모리 상에서 PNG 포맷으로 변환
        with io.BytesIO() as output:
            image.save(output, format='PNG')
            png_bytes = output.getvalue()

        # PNG 바이트를 Base64로 인코딩
        encoded_png = base64.b64encode(png_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{encoded_png}"
        # print(f"data_uri : {data_uri}")
        return data_uri

    except Exception as e:
        print("이미지 생성 중 오류 발생:", e)
        return None

def fetch_krunner_results(query:str)-> List[KRunnerResult]:
    """KRunner Match(query) 결과를 KRunnerResult 객체 리스트로 반환."""
    # D-Bus 세션 버스 연결
    bus = dbus.SessionBus()
    proxy = bus.get_object('org.kde.plasma.browser_integration', '/TabsRunner')
    interface = dbus.Interface(proxy, 'org.kde.krunner1')

    # Match 메서드 호출
    results = interface.Match(query)
    # DBus 자료를 일반 파이썬 자료형으로 변환
    converted_results = dbus_to_python(results)

    krunner_results = []

    if converted_results and isinstance(converted_results, list):
        for item in converted_results:
            # 보통 구조: (id, text, iconName, type, relevance, score, { 'icon-data':..., 'subtext':..., 'urls':... })
            # 예:
            # (
            #   '33',
            #   'KDE/plasma-browser-integration: Components necessary to integrate browsers into the Plasma Desktop',
            #   'firefox',
            #   70,
            #   0.9,
            #   {
            #       'actions': [],
            #       'icon-data': (32, 32, 128, True, 8, 4, [0,0,0,...]),
            #       'subtext': 'https://github.com/KDE/plasma-browser-integration',
            #       'urls': ['https://github.com/KDE/plasma-browser-integration']
            #   }
            # )

            if not isinstance(item, (tuple, list)):
                continue
            if len(item) < 6:
                continue

            # 튜플 구조 해석
            rid = item[0]   # '33'
            text = item[1]  # 'KDE/plasma-browser-integration...'
            # item[2] => 아이콘 이름('firefox') 등
            # item[3] => type(70)
            # item[4] => score(0.9)
            meta = item[5]  # 딕셔너리 형태( 'icon-data':..., 'subtext':..., 'urls':... )
            if not isinstance(meta, dict):
                continue

            # subtext, urls, icon_data 추출
            subtext = meta.get('subtext', None)
            urls = meta.get('urls', [])
            icon_data_tuple = meta.get('icon-data', None)

            # 아이콘 data URI 생성
            icon_data_uri = None
            if icon_data_tuple:
                icon_data_uri = extract_icon_data(icon_data_tuple)

            # KRunnerResult 객체 생성
            result_obj = KRunnerResult(
                rid=rid,
                text=text,
                icon_url=icon_data_uri,
                subtext=subtext,
                urls=urls
            )

            krunner_results.append(result_obj)

    return krunner_results


class Plugin(PluginInstance, TriggerQueryHandler):

    def __init__(self):
        PluginInstance.__init__(self)
        TriggerQueryHandler.__init__(
            self, self.id, self.name, self.description,
            defaultTrigger='f '
        )

    def handleTriggerQuery(self, query):
        stripped = query.string.strip()
        if stripped:
            print(f"current query : {stripped}")
            result = fetch_krunner_results(stripped)
            # print(f"ret : {result}")
            for ret in result:
                query.add(StandardItem(
                    id=self.id,
                    text=ret.text,
                    subtext=ret.subtext,
                    inputActionText=query.trigger + ret.text,
                    iconUrls = [ret.icon_url],
                    actions = [
                        Action("Switch Firefox Tab & Window", "Switch Firefox Tab & Window", lambda id=ret.rid: run_krunner_action(id))
                    ]
                ))
        
        # stripped = query.string.strip()
        # if stripped:
        #     try:
        #         result = eval(stripped)
        #     except Exception as ex:
        #         result = ex

        #     result_str = str(result)

        #     query.add(StandardItem(
        #         id=self.id,
        #         text=result_str,
        #         subtext=type(result).__name__,
        #         inputActionText=query.trigger + result_str,
        #         iconUrls= [main()],
        #         actions = [
        #             Action("copy", "Copy result to clipboard", lambda r=result_str: setClipboardText(r)),
        #             Action("exec", "Execute python code", lambda r=result_str: exec(stripped)),
        #         ]
        #     ))

```
