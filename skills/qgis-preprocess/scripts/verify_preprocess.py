# -*- coding: utf-8 -*-
"""projNN_*/01.preprocess 공통 전처리 감사.

합의된 9항목을 01.preprocess 안의 모든 gpkg·tif 에 적용해 PASS/FAIL/NA 를 판정한다.
판정만 하고 파일은 고치지 않는다 (고치는 것은 MCP 전처리 실행의 몫).

  1 파일 명명   pN_내용_5186.gpkg / pN_내용_5186.tif (소문자·숫자·밑줄만)
  2 포맷        벡터 GPKG · 래스터 GeoTIFF (레이어 0개인 GPKG 는 FAIL)
  3 좌표계      CRS 존재 여부 · EPSG:5186 여부 (비공간 테이블만 있으면 NA)
  4 인코딩      문자열 필드 표본(최대 2,000행)에 U+FFFD / 모지바케 패턴.
                비공간 테이블 레이어(인구표 등)도 같이 본다
  5 무결성      불량 지오메트리 · 널/빈 지오메트리 · 중복 지오메트리
  6 필드 타입   조인키 후보(cd/code/id)가 문자열인지 · 숫자로 보이는 문자열 필드 수.
                비공간 테이블 레이어도 같이 본다
  7 범위·해상도 대상지 시군구 경계와 교차 여부(PASS 기준) · within 과 교차 면적비 기록
                · 래스터 nodata·해상도
  8 공간 인덱스 GPKG 의 rtree_<table>_<geom> 테이블 존재 (sqlite3)
  9 기록        프로젝트별 로그 파일이 있고 행 수가 파일 수 x 항목 수 이상인지

항목 키 표기는 문서(handouts/PREPROCESS.md · docs/10 §6)와 같다:
  0.folder 1.naming 2.format 3.crs 4.encoding 5.integrity 6.field_type
  7a.extent 7b.raster 8.rtree 9.record

한계 (이 스크립트가 재지 않는 것):
  - ⑥ 은 조인키 후보 필드의 **타입만** 본다. 조인 양쪽(경계·CSV)의 같은 키가 서로
    같은 타입·같은 값 체계인지는 검사하지 않는다. 그건 실제 조인을 돌려 봐야 안다.
  - ⑤ 의 점 레이어 중복 지오메트리는 건수만 기록하고 FAIL 로 보지 않는다
    (같은 건물 안 다점포처럼 좌표 중복이 정상인 자료가 있다).
  - ④ 는 표본 2,000행까지만 본다. 뒤쪽 행의 인코딩 사고는 놓칠 수 있다.
  - ⑦ 은 bbox 사각형끼리의 교차만 본다(지오메트리 교차가 아니다).
  - 판정만 하고 파일은 고치지 않는다. 상태를 바꾸지 않으므로 `.aux.xml` 같은
    부수 파일도 만들지 않는다(GDAL_PAM_ENABLED=NO).

사용:
    python verify_preprocess.py                # P1~P10 전부
    python verify_preprocess.py --projects 2,5 # 일부만
    python verify_preprocess.py --log scripts/_logs/preprocess_audit_260912_final.csv

출력:
    projNN_*/01.preprocess/_preprocess_log.csv       (프로젝트별)
    scripts/_logs/preprocess_audit_YYMMDD.csv        (전체, --log 로 지정 가능)
    컬럼: date, project, file, item, measured, verdict, action, output
"""
import argparse
import csv
import io
import os
import re
import sqlite3
import sys
import time

# --- PROJ_LIB 고정 (rasterio 사용 전) -----------------------------------------
import rasterio  # noqa: E402

os.environ["PROJ_LIB"] = os.path.join(os.path.dirname(rasterio.__file__), "proj_data")
# 감사는 상태를 바꾸지 않는다. GDAL 이 래스터를 열 때 통계를 <파일>.aux.xml 로
# 흘리지 않도록 PAM 을 끈다 (2026-09-12: 01.preprocess 에 aux.xml 5개가 생겼다).
os.environ["GDAL_PAM_ENABLED"] = "NO"

import geopandas as gpd  # noqa: E402
import fiona  # noqa: E402
import pandas as pd  # noqa: E402

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(ROOT, "scripts", "_logs")
HEADER = ["date", "project", "file", "item", "measured", "verdict", "action", "output"]

DATA_ROOT = r"C:\qgis_mcp_class"
ADMIN_GPKG = os.path.join(DATA_ROOT, "_shared", "admin", "regions_5186.gpkg")

PROJ_DIR = {
    1: "proj01_suitability", 2: "proj02_trade_area", 3: "proj03_population",
    4: "proj04_park", 5: "proj05_terrain", 6: "proj06_realprice",
    7: "proj07_flood", 8: "proj08_network", 9: "proj09_landcover",
    10: "proj10_capstone",
}
PROJ_REGION = {
    1: "daejeon_yuseong", 2: "daejeon_seo", 3: "gwangju", 4: "cheongju",
    5: "wonju", 6: "daegu_suseong", 7: "wonju", 8: "jeonju", 9: "sejong",
    10: None,
}

# 1 파일 명명: pN_내용_5186.(gpkg|tif). 소문자·숫자·밑줄만, 한글·공백 금지.
NAME_RE = re.compile(r"^p(\d{1,2})_[a-z0-9_]+_5186\.(gpkg|tif)$")
# 4 모지바케: UTF-8 한글을 Latin-1/CP1252 로 잘못 읽었을 때 나오는 고위 라틴 연쇄
MOJIBAKE_RE = re.compile(r"[\u00c0-\u00ff][\u0080-\u00ff]")
NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?$")
# 6 조인키 후보 필드명
KEYFIELD_RE = re.compile(r"(^|_)(cd|code|id)(_|$)|cd$|code$|id$", re.I)

# ④ 인코딩 · ⑥ 숫자형 문자열 판별 표본 행 수 (2026-09-12: 200 → 2,000)
ENC_SAMPLE_ROWS = 2000
# 파일 1개당 감사 항목 수 (1.naming ~ 8.rtree) — ⑨ 기록 판정의 기준
ITEMS_PER_FILE = 9


class Audit(object):
    """전체 로그 + 프로젝트별 로그에 즉시 append + flush."""

    def __init__(self, global_path=None):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.date = time.strftime("%Y-%m-%d %H:%M:%S")
        self.gpath = global_path or os.path.join(
            LOG_DIR, time.strftime("preprocess_audit_%y%m%d.csv"))
        self._gf, self._gw = self._open(self.gpath)
        self._pf = {}
        self.counts = {}

    @staticmethod
    def _open(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        f = open(path, "a", newline="", encoding="utf-8-sig")
        w = csv.writer(f)
        if new:
            w.writerow(HEADER)
            f.flush()
        return f, w

    def project_log(self, pid):
        if pid in self._pf:
            return self._pf[pid]
        d = os.path.join(DATA_ROOT, PROJ_DIR[pid], "01.preprocess")
        self._pf[pid] = self._open(os.path.join(d, "_preprocess_log.csv"))
        return self._pf[pid]

    def row(self, pid, fname, item, measured, verdict, output="", global_only=False):
        """global_only=True 면 전체 로그에만 쓴다.

        01.preprocess 폴더가 없는 프로젝트에 프로젝트별 로그를 쓰면 폴더가 생겨
        "폴더 없음" 판정과 모순된다. 감사 스크립트는 상태를 바꾸지 않는다.
        """
        r = [self.date, "P%d" % pid, fname, item, measured, verdict, "audit", output]
        self._gw.writerow(r)
        self._gf.flush()
        if not global_only:
            f, w = self.project_log(pid)
            w.writerow(r)
            f.flush()
        self.counts[(pid, item)] = self.counts.get((pid, item), [])
        self.counts[(pid, item)].append(verdict)
        print("  P%-2d %-24s %-18s %-5s %s" % (pid, fname, item, verdict, measured))

    def close(self):
        self._gf.close()
        for f, _ in self._pf.values():
            f.close()


# --- 항목별 판정 --------------------------------------------------------------
def check_naming(path, pid):
    fn = os.path.basename(path)
    m = NAME_RE.match(fn)
    if not m:
        why = []
        if re.search(r"[^\x00-\x7f]", fn):
            why.append("비ASCII(한글)")
        if " " in fn:
            why.append("공백")
        if re.search(r"[A-Z]", fn):
            why.append("대문자")
        if not re.match(r"^p\d", fn):
            why.append("pN 접두 없음")
        if "_5186." not in fn:
            why.append("_5186 접미 없음")
        return "%s (%s)" % (fn, ", ".join(why) or "정규식 불일치"), "FAIL"
    if int(m.group(1)) != pid:
        return "%s (pN=%s, 프로젝트 P%d 와 불일치)" % (fn, m.group(1), pid), "FAIL"
    return fn, "PASS"


def check_format(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".gpkg":
        try:
            layers = fiona.listlayers(path)
            if not layers:
                # 레이어 0개 GPKG 는 포맷은 맞지만 입력으로 쓸 수 없다.
                return "GPKG 열림, 레이어 0개 (빈 파일)", "FAIL"
            return "GPKG 열림, 레이어 %d개 %s" % (len(layers), layers), "PASS"
        except Exception as e:
            return "GPKG 열기 실패: %s" % e, "FAIL"
    if ext in (".tif", ".tiff"):
        try:
            with rasterio.open(path) as ds:
                drv = ds.driver
            return "driver=%s" % drv, ("PASS" if drv == "GTiff" else "FAIL")
        except Exception as e:
            return "GeoTIFF 열기 실패: %s" % e, "FAIL"
    return "지원 대상 아님 (%s)" % ext, "NA"


def _noepsg_note(crs, width=40):
    """CRS 는 있는데 EPSG 코드로 식별되지 않을 때의 설명 문구.

    `to_epsg()` 는 기본 confidence 70 이다. ESRI 풍 WKT(예 AAIGrid 동반 `.prj` 의
    `DATUM["Korean_Geodetic_Datum_2002"]`)는 그 문턱을 넘지 못해 None 이 되는데,
    **CRS 태그가 없는 것과는 다른 상태**다. 둘을 같은 문구로 적으면 원인을 잘못 짚는다
    (2026-09-12 `p6_idw_price*.tif` 오기 사례 — docs/10 §8-5).
    확정 문구에 `EPSG:` 접두를 붙이지 않는다 — 판정이 문자열을 훑는 경우가 있다.
    """
    low = None
    try:
        low = crs.to_epsg(confidence_threshold=20)
    except Exception:
        pass
    return "CRS 있음, EPSG 미확정(confidence) — %s%s" % (
        str(crs)[:width], (" / confidence=20 에서 %s" % low) if low else "")


def check_crs_vector(gdfs, n_aspatial=0):
    """공간 레이어의 CRS. 비공간 테이블만 있는 파일은 NA (CRS 가 없는 게 정상)."""
    if not gdfs:
        return ("공간 레이어 없음 — 비공간 테이블 %d개뿐 (CRS 해당 없음)" % n_aspatial), "NA"
    out, codes = [], set()
    for name, g in gdfs:
        if g.crs is None:
            codes.add(None)
            out.append("%s: CRS 태그 없음" % name)
            continue
        code = None
        try:
            code = g.crs.to_epsg()
        except Exception:
            pass
        if code:
            codes.add(code)
            out.append("%s: EPSG:%s" % (name, code))
            continue
        codes.add("noepsg")
        out.append("%s: %s" % (name, _noepsg_note(g.crs, 40)))
    # 판정 규칙 불변: 전 레이어가 EPSG:5186 일 때만 PASS.
    # (문자열 훑기 대신 코드 집합으로 판정해 설명 문구 변경에 흔들리지 않게 했다)
    ok = bool(codes) and codes == {5186}
    return " / ".join(out) if out else "레이어 없음", ("PASS" if ok else "FAIL")


def check_crs_raster(path):
    with rasterio.open(path) as ds:
        if ds.crs is None:
            return "CRS 태그 없음", "FAIL"
        code = ds.crs.to_epsg()
        if code:
            return "EPSG:%s" % code, ("PASS" if code == 5186 else "FAIL")
        return _noepsg_note(ds.crs, 60), "FAIL"


def check_encoding(gdfs):
    """문자열 필드 표본에서 U+FFFD·모지바케 탐색.

    gdfs 에는 공간 레이어와 **비공간 테이블 레이어(인구표 등)를 함께** 넘긴다.
    깨진 한글은 지오메트리 유무와 무관하게 속성에서 난다.
    """
    bad_fields, n_fields, n_cells = [], 0, 0
    for name, g in gdfs:
        strcols = [c for c in g.columns
                   if c != "geometry" and pd.api.types.is_object_dtype(g[c])]
        n_fields += len(strcols)
        sample = g.head(ENC_SAMPLE_ROWS)
        for c in strcols:
            vals = sample[c].dropna().astype(str)
            n_cells += len(vals)
            hits = [v for v in vals if ("\ufffd" in v or MOJIBAKE_RE.search(v))]
            if hits:
                bad_fields.append("%s.%s(%d건 예:%r)" % (name, c, len(hits), hits[0][:20]))
    if not n_fields:
        return "문자열 필드 없음", "NA"
    if bad_fields:
        return "표본 %d셀 중 이상 %s" % (n_cells, "; ".join(bad_fields[:5])), "FAIL"
    return "문자열 필드 %d개 · 표본 %d셀, U+FFFD·모지바케 0" % (n_fields, n_cells), "PASS"


def check_integrity(gdfs):
    """불량·널/빈·중복 지오메트리 수.

    판정: 불량 또는 널/빈이 하나라도 있으면 FAIL.
    중복은 수를 반드시 기록하되, 점 레이어(상가·노드처럼 같은 건물에 여러 건이
    정상적으로 겹치는 자료)에서는 FAIL 로 보지 않는다. 선·면의 중복만 FAIL 이다.
    """
    inv = nul = emp = dup = 0
    dup_nonpoint = 0
    for _, g in gdfs:
        geom = g.geometry
        nul += int(geom.isna().sum())
        ok = geom.dropna()
        if not len(ok):
            continue
        emp += int(ok.is_empty.sum())
        inv += int((~ok.is_valid).sum())
        wkb = ok.to_wkb()
        d = int(len(wkb) - len(set(wkb)))
        dup += d
        if not set(ok.geom_type.unique()) <= {"Point", "MultiPoint"}:
            dup_nonpoint += d
    measured = "불량 %d · 널 %d · 빈 %d · 중복 %d (점 제외 중복 %d)" % (
        inv, nul, emp, dup, dup_nonpoint)
    bad = (inv > 0 or nul > 0 or emp > 0 or dup_nonpoint > 0)
    return measured, ("FAIL" if bad else "PASS")


def check_field_types(gdfs):
    """조인키 후보(cd/code/id) 필드의 타입.

    gdfs 에는 공간 레이어와 **비공간 테이블 레이어를 함께** 넘긴다 — 조인키 타입
    사고는 CSV 에서 온 비공간 테이블 쪽에서 주로 난다.
    한계: 조인 양쪽의 같은 키가 서로 같은 타입·값 체계인지는 재지 않는다.
    """
    nonstr_keys, numeric_like = [], []
    total_keys = 0
    for name, g in gdfs:
        for c in g.columns:
            if c == "geometry":
                continue
            if KEYFIELD_RE.search(c):
                total_keys += 1
                if not pd.api.types.is_object_dtype(g[c]):
                    nonstr_keys.append("%s.%s(%s)" % (name, c, g[c].dtype))
            if pd.api.types.is_object_dtype(g[c]):
                vals = g[c].dropna().astype(str)
                if len(vals) and all(NUMERIC_RE.match(v) for v in vals.head(ENC_SAMPLE_ROWS)):
                    numeric_like.append("%s.%s" % (name, c))
    measured = "조인키후보 %d개, 비문자열 %d개%s · 숫자형 문자열필드 %d개%s" % (
        total_keys, len(nonstr_keys),
        (" [%s]" % ", ".join(nonstr_keys[:5])) if nonstr_keys else "",
        len(numeric_like),
        (" [%s]" % ", ".join(numeric_like[:5])) if numeric_like else "")
    if total_keys == 0:
        return ("NA(후보 없음) — 조인키 후보(cd/code/id) 필드가 없어 판정 대상 아님 · "
                + measured), "NA"
    return measured, ("PASS" if not nonstr_keys else "FAIL")


def region_bounds(pid):
    key = PROJ_REGION.get(pid)
    if not key or not os.path.exists(ADMIN_GPKG):
        return None
    try:
        return gpd.read_file(ADMIN_GPKG, layer=key)
    except Exception:
        return None


def check_extent(bounds, reg):
    """bounds=(minx,miny,maxx,maxy). reg=GeoDataFrame.

    판정 규칙 (2026-09-12 확정):
      - 레이어 extent 가 대상지 경계와 **교차하면 PASS**. 전국·광역 자료를 그대로
        표준 입력으로 쓰는 경우(P8 전국 노드링크 등)가 정상이므로, "대상지 안에
        완전히 들어가는지" 를 판정 기준으로 쓰지 않는다.
      - 대상지 안에 완전히 들어가는지는 `within=True/False` 로 measured 에 기록만 한다.
      - **교차 0 이면 FAIL** — 지역이 틀렸거나 CRS 가 틀렸다는 신호다.
      - 대상지 클립은 선택이다(용량·속도 목적).
    교차 면적비 = (bbox 교차 사각형 면적) / (레이어 bbox 면적). 레이어 bbox 가
    선·점이라 면적이 0이면 NA 로 적는다.
    """
    if reg is None:
        return "대상지 경계 없음", "NA"
    rb = reg.total_bounds
    inter = not (bounds[2] < rb[0] or bounds[0] > rb[2]
                 or bounds[3] < rb[1] or bounds[1] > rb[3])
    within = (bounds[0] >= rb[0] and bounds[1] >= rb[1]
              and bounds[2] <= rb[2] and bounds[3] <= rb[3])
    lay_area = max(0.0, bounds[2] - bounds[0]) * max(0.0, bounds[3] - bounds[1])
    if inter:
        iw = min(bounds[2], rb[2]) - max(bounds[0], rb[0])
        ih = min(bounds[3], rb[3]) - max(bounds[1], rb[1])
        inter_area = max(0.0, iw) * max(0.0, ih)
    else:
        inter_area = 0.0
    ratio = ("%.4f" % (inter_area / lay_area)) if lay_area > 0 else "NA(레이어 bbox 면적 0)"
    measured = ("layer bbox=(%.1f,%.1f,%.1f,%.1f) region bbox=(%.1f,%.1f,%.1f,%.1f) "
                "intersects=%s within=%s 교차면적비=%s"
                % (bounds[0], bounds[1], bounds[2], bounds[3],
                   rb[0], rb[1], rb[2], rb[3], inter, within, ratio))
    return measured, ("PASS" if inter else "FAIL")


def check_raster_spec(path):
    with rasterio.open(path) as ds:
        nd = ds.nodata
        measured = "nodata=%s · res=%gx%g · %dx%d px · dtype=%s" % (
            nd, ds.res[0], ds.res[1], ds.width, ds.height, ds.dtypes[0])
    return measured, ("PASS" if nd is not None else "FAIL")


def check_spatial_index(path):
    try:
        con = sqlite3.connect(path)
        cur = con.cursor()
        cur.execute("SELECT table_name, column_name FROM gpkg_geometry_columns")
        geoms = cur.fetchall()
        cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")
        names = set(r[0] for r in cur.fetchall())
        con.close()
    except Exception as e:
        return "sqlite 조회 실패: %s" % e, "FAIL"
    missing, found = [], []
    for t, c in geoms:
        rt = "rtree_%s_%s" % (t, c)
        (found if rt in names else missing).append(rt)
    if not geoms:
        return "지오메트리 테이블 없음", "NA"
    measured = "있음 %s%s" % (found, (" / 없음 %s" % missing) if missing else "")
    return measured, ("PASS" if not missing else "FAIL")


# --- 파일 단위 감사 -----------------------------------------------------------
def audit_vector(au, pid, path, reg):
    fn = os.path.basename(path)
    out = path
    m, v = check_naming(path, pid)
    au.row(pid, fn, "1.naming", m, v, out)
    m, v = check_format(path)
    au.row(pid, fn, "2.format", m, v, out)
    try:
        layers = fiona.listlayers(path)
        alldfs = [(L, gpd.read_file(path, layer=L)) for L in layers]
        # 공간 레이어와 비공간 테이블 레이어(인구표 등)를 갈라 둔다.
        # ③ CRS·⑤ 무결성·⑦ 범위는 공간 레이어만, ④ 인코딩·⑥ 필드 타입은 둘 다 본다.
        gdfs = [(L, g) for L, g in alldfs if "geometry" in g.columns]
        tabs = [(L, g) for L, g in alldfs if "geometry" not in g.columns]
    except Exception as e:
        au.row(pid, fn, "3.crs", "읽기 실패: %s" % e, "FAIL", out)
        return
    m, v = check_crs_vector(gdfs, n_aspatial=len(tabs))
    au.row(pid, fn, "3.crs", m, v, out)
    m, v = check_encoding(alldfs)
    if tabs:
        m += " (비공간 테이블 %d개 포함: %s)" % (len(tabs), [L for L, _ in tabs])
    au.row(pid, fn, "4.encoding", m, v, out)
    if gdfs:
        m, v = check_integrity(gdfs)
    else:
        m, v = "비공간 테이블만 (지오메트리 없음)", "NA"
    au.row(pid, fn, "5.integrity", m, v, out)
    m, v = check_field_types(alldfs)
    if tabs:
        m += " (비공간 테이블 %d개 포함)" % len(tabs)
    au.row(pid, fn, "6.field_type", m, v, out)
    if gdfs:
        b = gdfs[0][1].total_bounds
        for _, g in gdfs[1:]:
            bb = g.total_bounds
            b = [min(b[0], bb[0]), min(b[1], bb[1]), max(b[2], bb[2]), max(b[3], bb[3])]
        m, v = check_extent(b, reg)
    else:
        m, v = "비공간 테이블만 (extent 없음)", "NA"
    au.row(pid, fn, "7a.extent", m, v, out)
    au.row(pid, fn, "7b.raster", "벡터", "NA", out)
    m, v = check_spatial_index(path)
    au.row(pid, fn, "8.rtree", m, v, out)


def audit_raster(au, pid, path, reg):
    fn = os.path.basename(path)
    out = path
    m, v = check_naming(path, pid)
    au.row(pid, fn, "1.naming", m, v, out)
    m, v = check_format(path)
    au.row(pid, fn, "2.format", m, v, out)
    try:
        m, v = check_crs_raster(path)
    except Exception as e:
        m, v = "읽기 실패: %s" % e, "FAIL"
    au.row(pid, fn, "3.crs", m, v, out)
    au.row(pid, fn, "4.encoding", "래스터(문자열 필드 없음)", "NA", out)
    au.row(pid, fn, "5.integrity", "래스터(지오메트리 없음)", "NA", out)
    au.row(pid, fn, "6.field_type", "래스터(속성 필드 없음)", "NA", out)
    try:
        with rasterio.open(path) as ds:
            b = (ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top)
        m, v = check_extent(b, reg)
    except Exception as e:
        m, v = "bounds 읽기 실패: %s" % e, "FAIL"
    au.row(pid, fn, "7a.extent", m, v, out)
    m, v = check_raster_spec(path)
    au.row(pid, fn, "7b.raster", m, v, out)
    au.row(pid, fn, "8.rtree", "래스터 N/A", "NA", out)


def check_record(pid, d, n_files):
    """⑨ 기록: 프로젝트별 로그 파일이 있고, 행 수가 파일 수 x 항목 수 이상인지.

    프로젝트 로그에는 MCP 실행 행과 감사 행이 함께 쌓이므로 하한만 본다.
    """
    path = os.path.join(d, "_preprocess_log.csv")
    if not os.path.exists(path):
        return "_preprocess_log.csv 없음: %s" % path, "FAIL"
    need = n_files * ITEMS_PER_FILE
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = sum(1 for _ in csv.reader(f))
    except Exception as e:
        return "_preprocess_log.csv 읽기 실패: %s" % e, "FAIL"
    data_rows = max(0, rows - 1)  # 헤더 제외
    measured = ("_preprocess_log.csv 데이터 %d행 · 필요 하한 %d행 (파일 %d개 x 항목 %d개)"
                % (data_rows, need, n_files, ITEMS_PER_FILE))
    return measured, ("PASS" if data_rows >= need else "FAIL")


def audit_project(au, pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid], "01.preprocess")
    if not os.path.isdir(d):
        au.row(pid, "-", "0.folder", "01.preprocess 폴더 없음: %s" % d, "NA", d,
               global_only=True)
        return 0
    files = sorted(f for f in os.listdir(d)
                   if os.path.splitext(f)[1].lower() in (".gpkg", ".tif", ".tiff"))
    if not files:
        # 감사 대상 파일이 0개면 프로젝트별 로그를 새로 만들지 않는다
        # (P7 처럼 다른 프로젝트 산출물을 공유하는 경우 · P10 처럼 점검 기록만 있는 경우).
        au.row(pid, "-", "0.folder", "01.preprocess 비어 있음 (gpkg·tif 0개)", "NA", d,
               global_only=True)
        return 0
    reg = region_bounds(pid)
    for f in files:
        p = os.path.join(d, f)
        if f.lower().endswith(".gpkg"):
            audit_vector(au, pid, p, reg)
        else:
            audit_raster(au, pid, p, reg)
    m, v = check_record(pid, d, len(files))
    au.row(pid, "_preprocess_log.csv", "9.record", m, v,
           os.path.join(d, "_preprocess_log.csv"))
    return len(files)


def main(argv=None):
    ap = argparse.ArgumentParser(description="01.preprocess 공통 전처리 감사")
    ap.add_argument("--projects", default="1,2,3,4,5,6,7,8,9,10",
                    help="대상 프로젝트 번호 (예: 2,5). 기본 전체")
    ap.add_argument("--log", default=None, help="전체 로그 경로 지정")
    args = ap.parse_args(argv)

    pids = [int(t.strip()) for t in args.projects.split(",") if t.strip()]
    au = Audit(args.log)
    print("[LOG] %s" % au.gpath)
    total = 0
    try:
        for pid in pids:
            if pid not in PROJ_DIR:
                print("  skip unknown project %s" % pid)
                continue
            total += audit_project(au, pid)
    finally:
        au.close()

    # 요약
    print("\n프로젝트 x 항목 요약 (PASS/FAIL/NA)")
    items = sorted(set(k[1] for k in au.counts))
    print("  %-5s %s" % ("proj", " ".join("%-16s" % i for i in items)))
    for pid in pids:
        cells = []
        for it in items:
            v = au.counts.get((pid, it))
            if not v:
                cells.append("%-16s" % "-")
            else:
                cells.append("%-16s" % ("%dP/%dF/%dN" % (v.count("PASS"),
                                                         v.count("FAIL"),
                                                         v.count("NA"))))
        print("  P%-4d %s" % (pid, " ".join(cells)))
    print("\n감사 파일 %d개 · 로그 %s" % (total, au.gpath))
    return 0


if __name__ == "__main__":
    sys.exit(main())
