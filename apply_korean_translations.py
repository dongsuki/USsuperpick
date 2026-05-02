"""
한글명 일괄 적용 스크립트 (1회성).

_korean_names_pending.json의 record_id로 Airtable에 한글 음역을 채워넣는다.
TRANSLATIONS dict는 Claude(LLM)가 188개 영문명을 음역해서 직접 작성한 결과.

사용법:
  $env:AIRTABLE_PAT="patXXX..."
  python apply_korean_translations.py
"""

import os
import sys
import json
import time
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_ID = "appAh82iPV3cH6Xx5"
TABLE_ID = "tbljCB2CnDe2eWB3M"
URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"

# Ticker → 한글 음역 매핑 (Claude가 작성)
TRANSLATIONS = {
    "AXTI": "AXT", "BE": "블룸에너지", "PL": "플래닛 랩스", "CIEN": "시에나",
    "RAPT": "RAPT", "SPHR": "스피어 엔터테인먼트", "NGL": "NGL 에너지 파트너스",
    "COHR": "코히어런트", "AGX": "아르간", "FIX": "컴포트 시스템스",
    "CLS": "셀레스티카", "ASX": "ASE 테크놀로지", "TPC": "튜터 페리니",
    "DOCN": "디지털오션", "VRT": "버티브", "GLW": "코닝", "PACS": "PACS 그룹",
    "NEXA": "넥사 리소시스", "STM": "ST마이크로일렉트로닉스", "NOK": "노키아",
    "MOD": "모다인", "CSTM": "콘스텔리움", "SEI": "솔라리스 에너지",
    "PUMP": "프로페트로", "GEV": "GE 버노바", "CTOS": "커스텀 트럭 원 소스",
    "GHM": "그레이엄", "AVNS": "아바노스 메디컬", "ONTO": "온토 이노베이션",
    "CC": "케머스", "CAT": "캐터필러", "KEYS": "키사이트 테크놀로지스",
    "APA": "APA", "INSW": "인터내셔널 시웨이스", "VSH": "비셰이",
    "CVE": "세노버스 에너지", "THR": "써몬 그룹", "LXU": "LSB 인더스트리스",
    "PWR": "콴타 서비스", "DAN": "다나", "VSCO": "빅토리아 시크릿",
    "KLAC": "KLA", "DY": "다이콤 인더스트리스", "DELL": "델 테크놀로지스",
    "DCO": "듀코먼", "TDW": "타이드워터", "PBF": "PBF 에너지",
    "ESI": "엘리먼트 솔루션스", "AVDL": "AVDL", "CCJ": "카메코",
    "GRC": "고먼-럽", "TDAY": "USA 투데이", "VET": "버밀리언 에너지",
    "ROG": "로저스", "AAMI": "아카디안 자산운용", "AMPY": "앰플리파이 에너지",
    "TSM": "TSMC", "CMI": "커민스", "PBR": "페트로브라스",
    "DAR": "달링 인그리디언츠", "DINO": "HF 싱클레어", "VLO": "발레로 에너지",
    "STNG": "스콜피오 탱커스", "HLIO": "헬리오스 테크놀로지스",
    "HP": "헬머리치 앤 페인", "RNG": "링센트럴", "CMRE": "코스타마레",
    "PBR-A": "페트로브라스(우선주)", "SKM": "SK텔레콤",
    "RRX": "리갈 렉스노드", "NUE": "뉴코", "HAFN": "하프니아",
    "XPRO": "엑스프로 그룹", "E": "ENI", "SU": "선코 에너지",
    "CMP": "콤파스 미네랄스", "TFII": "TFI 인터내셔널", "EQNR": "에퀴노르",
    "MOV": "모바도 그룹", "PLOW": "더글러스 다이내믹스",
    "ANET": "아리스타 네트웍스", "QUAD": "쿼드 그래픽스",
    "FTK": "플로텍 인더스트리스", "FDX": "페덱스", "GLDD": "GLDD",
    "BWA": "보그워너", "OPY": "오펜하이머", "WDS": "우드사이드 에너지",
    "NEM": "뉴몬트", "ATEN": "A10 네트웍스", "ENVA": "에노바 인터내셔널",
    "AIR": "AAR", "GNK": "젠코 시핑", "SLB": "SLB",
    "CM": "캐나다 임페리얼 뱅크 오브 커머스", "CRGY": "크레센트 에너지",
    "MPC": "마라톤 페트롤리엄", "C": "씨티그룹", "OOMA": "우마",
    "MOFG": "MOFG", "INVX": "이노벡스 인터내셔널", "ELPC": "코펠",
    "TRGP": "타가 리소시스", "VMI": "발몬트 인더스트리스",
    "MLI": "뮬러 인더스트리스", "MATX": "맷슨", "UVE": "유니버설 인슈어런스",
    "MD": "페디아트릭스 메디컬", "TTE": "토탈에너지스", "AZZ": "AZZ",
    "HCC": "워리어 멧 콜", "CNQ": "캐나디언 내추럴 리소시스",
    "RIO": "리오 틴토", "SCCO": "서던 코퍼", "TD": "토론토 도미니언 뱅크",
    "PSX": "필립스 66", "WSR": "화이트스톤 REIT", "KNX": "나이트-스위프트",
    "BHP": "BHP 그룹", "TPH": "트라이 포인트 홈스", "BP": "BP",
    "JCI": "존슨 컨트롤스", "VALE": "발리", "TEX": "테렉스",
    "MTW": "마니토웍", "HSBC": "HSBC홀딩스", "BK": "BNY 멜론",
    "CSX": "CSX", "APH": "암페놀", "MFG": "미즈호 파이낸셜",
    "NVEC": "NVE", "ALSN": "앨리슨 트랜스미션", "NVST": "엔비스타",
    "BC": "브런즈윅", "DTM": "DT 미드스트림", "SAN": "방코 산탄데르",
    "MUSA": "머피 USA", "BMO": "몬트리올 은행", "OXY": "옥시덴탈 페트롤리엄",
    "UNF": "유니퍼스트", "HWM": "하우멧 에어로스페이스", "MS": "모건스탠리",
    "DAL": "델타 항공", "GS": "골드만삭스", "FLOC": "플로코 홀딩스",
    "SPB": "스펙트럼 브랜즈", "AMX": "아메리카 모빌", "DAC": "다나오스",
    "WLK": "웨스트레이크", "MTX": "미네랄스 테크놀로지스",
    "ABX": "아바커스 글로벌", "GRDN": "가디언 파머시",
    "BNS": "노바스코샤은행", "HRTG": "헤리티지 인슈어런스",
    "WBS": "웹스터 파이낸셜", "NYT": "뉴욕타임스", "GM": "제너럴모터스",
    "BLFY": "BLFY", "RY": "캐나다 로열뱅크", "SMFG": "스미토모 미쓰이",
    "GFR": "그린파이어 리소시스", "FERG": "퍼거슨", "GFF": "그리폰",
    "RNGR": "레인저 에너지", "TGT": "타겟", "WELL": "웰타워",
    "WAB": "왑텍", "FCX": "프리포트-맥모란", "NEE": "넥스트에라 에너지",
    "TIMB": "TIM 브라질", "XOM": "엑슨모빌", "COP": "코노코필립스",
    "WPM": "휘튼 프레셔스 메탈스", "STEL": "스텔라 뱅코프",
    "MCB": "메트로폴리탄 뱅크", "ETR": "엔터지", "GPRK": "지오파크",
    "TRP": "TC 에너지", "PAGP": "플레인스 GP", "NSC": "노포크 서던",
    "GMED": "글로버스 메디컬", "AMTB": "아메란트 뱅코프",
    "BEP": "브룩필드 리뉴어블 파트너스", "IMAX": "아이맥스",
    "BDX": "벡톤 디킨슨", "ING": "ING 그룹", "CVX": "셰브론",
    "AIT": "어플라이드 인더스트리얼 테크놀로지스",
}


def main():
    pat = os.getenv("AIRTABLE_PAT")
    if not pat:
        print("❌ AIRTABLE_PAT 환경변수 필요")
        sys.exit(1)

    pending_path = os.path.join(os.path.dirname(__file__), "_korean_names_pending.json")
    if not os.path.exists(pending_path):
        print(f"❌ {pending_path} 없음")
        sys.exit(1)

    with open(pending_path, "r", encoding="utf-8") as f:
        pending = json.load(f)

    print(f"📋 대상 종목: {len(pending)}개")
    print(f"📝 음역 매핑: {len(TRANSLATIONS)}개\n")

    # batch_update 페이로드 준비 (record_id + 한글명)
    batch_payloads = []
    skipped = []
    for rec in pending:
        ticker = rec["ticker"]
        if ticker in TRANSLATIONS:
            batch_payloads.append({
                "id": rec["id"],
                "fields": {"한글명": TRANSLATIONS[ticker]},
            })
        else:
            skipped.append(ticker)

    if skipped:
        print(f"⚠️ 매핑 없음 ({len(skipped)}개): {', '.join(skipped[:20])}{'...' if len(skipped) > 20 else ''}")

    print(f"🚀 업데이트 시작: {len(batch_payloads)}개\n")

    # Airtable PATCH는 한 번에 최대 10개
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }
    success = 0
    errors = 0
    for i in range(0, len(batch_payloads), 10):
        batch = batch_payloads[i:i + 10]
        body = {"records": batch}
        try:
            r = requests.patch(URL, headers=headers, json=body, timeout=15)
            if r.status_code == 200:
                success += len(batch)
                print(f"  ✅ {i + len(batch)}/{len(batch_payloads)}")
            else:
                errors += len(batch)
                print(f"  ❌ batch {i//10 + 1}: {r.status_code} {r.text[:200]}")
        except Exception as e:
            errors += len(batch)
            print(f"  ❌ batch {i//10 + 1} 예외: {e}")
        time.sleep(0.25)  # rate limit

    print(f"\n📊 결과: 성공 {success}개, 에러 {errors}개")


if __name__ == "__main__":
    main()
