# -*- coding: utf-8 -*-
"""P1~P10 산출 파일에서 핵심 수치를 직접 재계산한다.

docs/8b.methodology_verify_v1.md §1 표의 "재계산값" 방법을 스크립트로 고정한 것이다.
보고서·로그의 숫자를 읽어오지 않고 `C:\\qgis_mcp_class\\projNN_*` 의 산출 파일에서
geopandas / rasterio / numpy 로 매번 다시 계산한다.

사용:
    python verify_outputs.py                  # P1~P10 전부 재계산
    python verify_outputs.py --projects 2,3   # 일부만
    python verify_outputs.py --template       # 재계산 + 04.verify/verify_pN.csv 생성

출력:
    scripts/_logs/verify_YYMMDD.csv   (date, project, metric, value, unit, source_file, method)
    projNN_*/04.verify/verify_pN.csv  (--template, 수동 검증 대조표)
        컬럼: metric, label, mcp_value, manual_value, diff, tolerance, verdict, note
        `metric` 은 기계 ID, `label` 은 `data_projects.py` 의 `verify_metrics` 지표명이다.
        한 지표가 여러 세부 행으로 나뉜다(예: "후보지 수" → p1_candidate_count ·
        p1_top_count). label 이 `(추가)` 로 시작하는 행은 verify_metrics 에 없는 보조 행이다.

산출 파일이 없으면 해당 metric 행을 value=NA · method=missing 으로 남기고 계속 진행한다.
"""
import argparse
import csv
import io
import os
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

# --- PROJ_LIB 고정 -----------------------------------------------------------
# 이 PC 는 PROJ_LIB 이 PostgreSQL 의 구버전 proj.db 를 가리켜 rasterio 가 CRS 를
# LOCAL_CS 로 잘못 읽는다. rasterio 를 쓰기 전에 번들 proj_data 로 바꾼다.
import rasterio  # noqa: E402  (경로 계산 목적의 선행 import)

os.environ["PROJ_LIB"] = os.path.join(os.path.dirname(rasterio.__file__), "proj_data")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import geopandas as gpd  # noqa: E402

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --- 경로 --------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(ROOT, "scripts", "_logs")
LOG_HEADER = ["date", "project", "metric", "value", "unit", "source_file", "method"]

DATA_ROOT = r"C:\qgis_mcp_class"
ADMIN_GPKG = os.path.join(DATA_ROOT, "_shared", "admin", "regions_5186.gpkg")

PROJ_DIR = {
    1: "proj01_suitability",
    2: "proj02_trade_area",
    3: "proj03_population",
    4: "proj04_park",
    5: "proj05_terrain",
    6: "proj06_realprice",
    7: "proj07_flood",
    8: "proj08_network",
    9: "proj09_landcover",
    10: "proj10_capstone",
}

# 프로젝트 대상지 (regions_5186.gpkg 레이어명)
PROJ_REGION = {
    1: "daejeon_yuseong", 2: "daejeon_seo", 3: "gwangju", 4: "cheongju",
    5: "wonju", 6: "daegu_suseong", 7: "wonju", 8: "jeonju", 9: "sejong",
    10: None,
}

# 지표 유형별 기본 허용오차 (--template 의 tolerance 열)
TOL = {
    "count": "0",
    "area": "0.1%",
    "length": "0.1%",
    "ratio": "0.1%",
    "size": "0.1%",
    "raster": "0.01%",
    "flag": "0",
}


# --- 로그 --------------------------------------------------------------------
class Log(object):
    """verify_YYMMDD.csv 즉시 append + flush."""

    def __init__(self, path=None):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.path = path or os.path.join(LOG_DIR, time.strftime("verify_%y%m%d.csv"))
        self.date = time.strftime("%Y-%m-%d %H:%M:%S")
        new = not os.path.exists(self.path) or os.path.getsize(self.path) == 0
        self._f = open(self.path, "a", newline="", encoding="utf-8-sig")
        self._w = csv.writer(self._f)
        if new:
            self._w.writerow(LOG_HEADER)
            self._f.flush()

    def write(self, m):
        self._w.writerow([self.date, m["project"], m["metric"], m["value"],
                          m["unit"], m["source_file"], m["method"]])
        self._f.flush()

    def close(self):
        self._f.close()


# --- 공통 도우미 --------------------------------------------------------------
def rel(path):
    """DATA_ROOT 기준 상대경로 (로그 가독성용)."""
    try:
        return os.path.relpath(path, DATA_ROOT).replace("\\", "/")
    except ValueError:
        return path


def metric(project, name, value, unit, src, method, kind="count", manual=False):
    return {"project": project, "metric": name, "value": value, "unit": unit,
            "source_file": rel(src) if src else "", "method": method,
            "kind": kind, "manual": manual}


def missing(project, name, unit, src, kind="count", manual=False):
    return metric(project, name, "NA", unit, src, "missing", kind, manual)


def fmt(x, nd=4):
    if x is None:
        return "NA"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return ("%%.%df" % nd) % float(x)


def read_vec(path, layer=None):
    """벡터 읽기. 없으면 None."""
    if not os.path.exists(path):
        return None
    return gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)


def region_gdf(pid):
    key = PROJ_REGION.get(pid)
    if not key or not os.path.exists(ADMIN_GPKG):
        return None
    return gpd.read_file(ADMIN_GPKG, layer=key)


def raster_stats(path, band=1):
    """nodata 제외 통계. 반환 dict 또는 None."""
    if not os.path.exists(path):
        return None
    with rasterio.open(path) as ds:
        a = ds.read(band, masked=True)
        valid = a.compressed()
        return {
            "width": ds.width, "height": ds.height,
            "resx": ds.res[0], "resy": ds.res[1],
            "crs": str(ds.crs.to_string()) if ds.crs else "",
            "nodata": ds.nodata, "dtype": ds.dtypes[band - 1],
            "count": int(valid.size),
            "min": float(valid.min()) if valid.size else None,
            "max": float(valid.max()) if valid.size else None,
            # float32 배열에서 바로 mean 을 내면 누적 오차로 소수 4째 자리가 흔들린다
            # (p6 클립 627.2987 vs 627.2988). float64 로 올려서 누적한다.
            "mean": float(valid.astype("float64").mean()) if valid.size else None,
            "cell_m2": abs(ds.res[0] * ds.res[1]),
        }


def unique_counts(path, band=1):
    """nodata 제외 고유값·개수."""
    if not os.path.exists(path):
        return None
    with rasterio.open(path) as ds:
        a = ds.read(band, masked=True)
        v, c = np.unique(a.compressed(), return_counts=True)
        return v, c, abs(ds.res[0] * ds.res[1])


# --- P1 ----------------------------------------------------------------------
def verify_p1(pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid])
    out = []
    cand = os.path.join(d, "02.analysis", "p1_candidate.gpkg")
    g = read_vec(cand)
    if g is None:
        out += [missing("P1", "p1_candidate_count", "면", cand, "count", True),
                missing("P1", "p1_candidate_area_km2", "km2", cand, "area", True),
                missing("P1", "p1_suit_score_min", "점", cand, "raster"),
                missing("P1", "p1_suit_score_max", "점", cand, "raster"),
                missing("P1", "p1_suit_score_mean", "점", cand, "raster")]
    else:
        out.append(metric("P1", "p1_candidate_count", len(g), "면", cand,
                          "geopandas 피처 수", "count", True))
        out.append(metric("P1", "p1_candidate_area_km2", fmt(g.geometry.area.sum() / 1e6),
                          "km2", cand, "지오메트리 면적 합 / 1e6", "area", True))
        if "suit_score" in g.columns:
            s = g["suit_score"].astype(float)
            out.append(metric("P1", "p1_suit_score_min", fmt(s.min()), "점", cand, "속성 min", "raster"))
            out.append(metric("P1", "p1_suit_score_max", fmt(s.max()), "점", cand, "속성 max", "raster"))
            out.append(metric("P1", "p1_suit_score_mean", fmt(s.mean()), "점", cand, "속성 mean", "raster"))
        out.append(metric("P1", "p1_min_polygon_m2", fmt(g.geometry.area.min()), "m2", cand,
                          "지오메트리 면적 min (슬리버 확인)", "area"))

    top = os.path.join(d, "03.outputs", "p1_top_sites.gpkg")
    gt = read_vec(top)
    if gt is None:
        out += [missing("P1", "p1_top_count", "면", top, "count", True),
                missing("P1", "p1_top_area_km2", "km2", top, "area", True)]
    else:
        out.append(metric("P1", "p1_top_count", len(gt), "면", top,
                          "geopandas 피처 수", "count", True))
        out.append(metric("P1", "p1_top_area_km2", fmt(gt.geometry.area.sum() / 1e6),
                          "km2", top, "지오메트리 면적 합 / 1e6", "area", True))
    return out


# --- P2 ----------------------------------------------------------------------
def verify_p2(pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid])
    out = []
    store = os.path.join(d, "01.preprocess", "p2_store_5186.gpkg")
    g = read_vec(store)
    if g is None:
        out.append(missing("P2", "p2_store_count", "개", store, "count"))
    else:
        out.append(metric("P2", "p2_store_count", len(g), "개", store,
                          "geopandas 피처 수", "count"))

    csv_path = os.path.join(d, "00.origins", "store_daejeon_seogu.csv")
    if not os.path.exists(csv_path):
        out.append(missing("P2", "p2_store_csv_rows", "행", csv_path, "count"))
    else:
        df = pd.read_csv(csv_path, low_memory=False)
        out.append(metric("P2", "p2_store_csv_rows", len(df), "행", csv_path,
                          "pandas 행 수", "count"))
        if "lon" in df.columns and "lat" in df.columns:
            out.append(metric("P2", "p2_store_coord_null",
                              int(df["lon"].isna().sum() + df["lat"].isna().sum()),
                              "건", csv_path, "lon/lat 결측 합", "count"))

    kde = os.path.join(d, "02.analysis", "p2_store_kde300.tif")
    st = raster_stats(kde)
    if st is None:
        out += [missing("P2", "p2_kde_max", "값", kde, "raster"),
                missing("P2", "p2_kde_size", "px", kde, "flag")]
    else:
        out.append(metric("P2", "p2_kde_max", "%.10f" % st["max"], "값", kde,
                          "rasterio nodata 제외 max", "raster"))
        out.append(metric("P2", "p2_kde_size", "%dx%d@%.0fm" % (st["width"], st["height"], st["resx"]),
                          "px", kde, "rasterio width/height/res", "flag"))

    hot = os.path.join(d, "02.analysis", "p2_hot_service_count.gpkg")
    gh = read_vec(hot)
    if gh is None or "NUMPOINTS" not in (gh.columns if gh is not None else []):
        out.append(missing("P2", "p2_hot_service_store_count", "개", hot, "count", True))
    else:
        out.append(metric("P2", "p2_hot_service_store_count",
                          int(gh["NUMPOINTS"].sum()), "개", hot,
                          "countpointsinpolygon 결과 NUMPOINTS 합", "count", True))

    # 6,441 은 native:buffer SEGMENTS=36 산출면(실효 반경 999.84 m) 안의 점 수다.
    # "1 km 내" 라는 표현이 버퍼 근사인지 확인하려면 정확한 유클리드 거리로 다시 센다.
    ctr = os.path.join(d, "02.analysis", "p2_hot_center.gpkg")
    gc = read_vec(ctr)
    if gc is None or g is None:
        out.append(missing("P2", "p2_hot_service_store_count_r1000", "개", ctr, "count"))
    else:
        c = gc.geometry.iloc[0]
        n_r = int((g.geometry.distance(c) <= 1000.0).sum())
        out.append(metric("P2", "p2_hot_service_store_count_r1000", n_r, "개", ctr,
                          "최대 셀 중심 (%.1f, %.1f) 에서 유클리드 거리 <= 1000 m 인 "
                          "상가 점 수 (버퍼 근사 아님)" % (c.x, c.y), "count"))

    bnd = os.path.join(d, "02.analysis", "p2_boundary_count.gpkg")
    gb = read_vec(bnd)
    if gb is None or "store_cnt" not in (gb.columns if gb is not None else []):
        out.append(missing("P2", "p2_boundary_store_count", "개", bnd, "count"))
    else:
        out.append(metric("P2", "p2_boundary_store_count", int(gb["store_cnt"].sum()),
                          "개", bnd, "경계 전체 집계 store_cnt", "count"))
        if gh is not None and "NUMPOINTS" in gh.columns and gb["store_cnt"].sum():
            share = 100.0 * gh["NUMPOINTS"].sum() / gb["store_cnt"].sum()
            out.append(metric("P2", "p2_hot_service_share_pct", fmt(share, 2), "%", hot,
                              "hot 1km 내 / 경계 전체 * 100", "ratio"))
    return out


# --- P3 ----------------------------------------------------------------------
def verify_p3(pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid])
    out = []
    sido = os.path.join(d, "00.origins", "sgis_sido_5186.gpkg")
    g = read_vec(sido, layer="sido_boundary")
    if g is None:
        out.append(missing("P3", "p3_sido_count", "개", sido, "count"))
    else:
        out.append(metric("P3", "p3_sido_count", len(g), "개", sido,
                          "sido_boundary 피처 수", "count"))

    sj = os.path.join(d, "02.analysis", "p3_sido_joined.gpkg")
    gj = read_vec(sj)
    if gj is None:
        out.append(missing("P3", "p3_sido_joined_count", "건", sj, "count", True))
    else:
        n = int(gj["tot_ppltn"].notna().sum()) if "tot_ppltn" in gj.columns else len(gj)
        out.append(metric("P3", "p3_sido_joined_count", n, "건", sj,
                          "tot_ppltn 비결측 행 수", "count", True))

    gw = os.path.join(d, "02.analysis", "p3_sido_gwangju.gpkg")
    gg = read_vec(gw)
    if gg is None:
        out.append(missing("P3", "p3_gwangju_extract_count", "건", gw, "count"))
    else:
        out.append(metric("P3", "p3_gwangju_extract_count", len(gg), "건", gw,
                          "extractbyexpression 결과 피처 수", "count"))

    emd = os.path.join(d, "02.analysis", "p3_emd_valid_v2.gpkg")
    ge = read_vec(emd)
    if ge is None:
        out += [missing("P3", "p3_emd_valid_count", "개", emd, "count", True),
                missing("P3", "p3_pop_dens_min", "명/km2", emd, "area"),
                missing("P3", "p3_pop_dens_max", "명/km2", emd, "area", True),
                missing("P3", "p3_pop_dens_mean", "명/km2", emd, "area"),
                missing("P3", "p3_total_pop", "명", emd, "count")]
    else:
        out.append(metric("P3", "p3_emd_valid_count", len(ge), "개", emd,
                          "geopandas 피처 수", "count", True))
        dens = ge["tot_ppltn"].astype(float) / (ge.geometry.area / 1e6)
        out.append(metric("P3", "p3_pop_dens_min", fmt(dens.min(), 3), "명/km2", emd,
                          "tot_ppltn / (지오메트리 면적/1e6) 의 min", "area"))
        out.append(metric("P3", "p3_pop_dens_max", fmt(dens.max(), 3), "명/km2", emd,
                          "tot_ppltn / (지오메트리 면적/1e6) 의 max", "area", True))
        out.append(metric("P3", "p3_pop_dens_mean", fmt(dens.mean(), 3), "명/km2", emd,
                          "tot_ppltn / (지오메트리 면적/1e6) 의 mean", "area"))
        out.append(metric("P3", "p3_total_pop", int(ge["tot_ppltn"].sum()), "명", emd,
                          "tot_ppltn 합", "count"))
    return out


# --- P4 ----------------------------------------------------------------------
def verify_p4(pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid])
    out = []
    parks = os.path.join(d, "02.analysis", "p4_parks.gpkg")
    g = read_vec(parks)
    if g is None:
        out.append(missing("P4", "p4_park_count", "면", parks, "count"))
    else:
        out.append(metric("P4", "p4_park_count", len(g), "면", parks,
                          "geopandas 피처 수", "count"))

    und = os.path.join(d, "02.analysis", "p4_underserved.gpkg")
    gu = read_vec(und)
    reg = region_gdf(pid)
    reg_km2 = float(reg.geometry.area.sum() / 1e6) if reg is not None else None
    if gu is None:
        out += [missing("P4", "p4_underserved_area_km2", "km2", und, "area"),
                missing("P4", "p4_underserved_ratio_pct", "%", und, "ratio")]
    else:
        ua = float(gu.geometry.area.sum() / 1e6)
        out.append(metric("P4", "p4_underserved_area_km2", fmt(ua, 3), "km2", und,
                          "지오메트리 면적 합 / 1e6", "area"))
        if reg_km2:
            out.append(metric("P4", "p4_underserved_ratio_pct", fmt(100.0 * ua / reg_km2, 2),
                              "%", und, "소외면적 / 시군구경계 면적 * 100", "ratio"))
            out.append(metric("P4", "p4_region_area_km2", fmt(reg_km2, 3), "km2", ADMIN_GPKG,
                              "regions_5186 cheongju 지오메트리 면적", "area"))

    ube = os.path.join(d, "02.analysis", "p4_under_by_emd.gpkg")
    gb = read_vec(ube)
    pop_total = None
    pop_src = os.path.join(d, "00.origins", "sgis_cheongju_5186.gpkg")
    gp = read_vec(pop_src, layer="emd_pop")
    if gp is not None and "tot_ppltn" in gp.columns:
        pop_total = float(gp["tot_ppltn"].sum())
        out.append(metric("P4", "p4_pop_total", int(pop_total), "명", pop_src,
                          "emd_pop tot_ppltn 합", "count"))
    else:
        out.append(missing("P4", "p4_pop_total", "명", pop_src, "count"))

    if gb is None or "pop_under" not in (gb.columns if gb is not None else []):
        out += [missing("P4", "p4_pop_underserved", "명", ube, "area", True),
                missing("P4", "p4_pop_underserved_ratio_pct", "%", ube, "ratio"),
                missing("P4", "p4_emd_intersect_count", "개", ube, "count")]
    else:
        pu = float(gb["pop_under"].sum())
        # 면적가중 안분 결과라 정수 일치를 요구할 수 없다 -> 면적계 허용오차(0.1%)를 쓴다.
        out.append(metric("P4", "p4_pop_underserved", fmt(pu, 1), "명", ube,
                          "면적가중 안분 pop_under 합", "area", True))
        out.append(metric("P4", "p4_emd_intersect_count", len(gb), "개", ube,
                          "교차 읍면동 피처 수", "count"))
        if pop_total:
            out.append(metric("P4", "p4_pop_underserved_ratio_pct", fmt(100.0 * pu / pop_total, 2),
                              "%", ube, "소외인구 / 총인구 * 100", "ratio"))
    return out


# --- P5 ----------------------------------------------------------------------
def verify_p5(pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid])
    out = []
    # 2026-09-12: ① 공통 전처리 명명 규칙 적용으로 p5_dem_wonju.tif -> p5_dem_wonju_5186.tif
    dem = os.path.join(d, "01.preprocess", "p5_dem_wonju_5186.tif")
    st = raster_stats(dem)
    if st is None:
        out += [missing("P5", "p5_dem_size", "px", dem, "flag"),
                missing("P5", "p5_elev_min", "m", dem, "raster"),
                missing("P5", "p5_elev_max", "m", dem, "raster")]
    else:
        out.append(metric("P5", "p5_dem_size", "%dx%d@%.0fm" % (st["width"], st["height"], st["resx"]),
                          "px", dem, "rasterio width/height/res", "flag"))
        out.append(metric("P5", "p5_elev_min", fmt(st["min"], 3), "m", dem,
                          "rasterio nodata 제외 min", "raster"))
        out.append(metric("P5", "p5_elev_max", fmt(st["max"], 3), "m", dem,
                          "rasterio nodata 제외 max", "raster"))

    zs = os.path.join(d, "03.outputs", "p5_elev_zone_slope.gpkg")
    g = read_vec(zs)
    reg = region_gdf(pid)
    if g is None:
        out += [missing("P5", "p5_zone_count", "면", zs, "count"),
                missing("P5", "p5_zone_area_sum_km2", "km2", zs, "area", True),
                missing("P5", "p5_zone_slope_mean_cls1", "도", zs, "raster", True),
                missing("P5", "p5_zone_slope_mean_cls17", "도", zs, "raster", True),
                missing("P5", "p5_slope_monotonic_upto", "구간", zs, "flag")]
    else:
        out.append(metric("P5", "p5_zone_count", len(g), "면", zs,
                          "geopandas 피처 수", "count"))
        za = float(g.geometry.area.sum() / 1e6)
        out.append(metric("P5", "p5_zone_area_sum_km2", fmt(za, 3), "km2", zs,
                          "지오메트리 면적 합 / 1e6", "area", True))
        if reg is not None:
            ra = float(reg.geometry.area.sum() / 1e6)
            out.append(metric("P5", "p5_region_area_km2", fmt(ra, 3), "km2", ADMIN_GPKG,
                              "regions_5186 wonju 지오메트리 면적", "area"))
            out.append(metric("P5", "p5_zone_area_diff_pct", fmt(100.0 * abs(za - ra) / ra, 4),
                              "%", zs, "|표고대합 - 경계면적| / 경계면적 * 100", "ratio"))
        if {"elev_cls", "slp_mean"}.issubset(g.columns):
            s = g[["elev_cls", "slp_mean"]].dropna().sort_values("elev_cls")
            s = s.reset_index(drop=True)
            k = 1
            for i in range(1, len(s)):
                if s.loc[i, "slp_mean"] > s.loc[i - 1, "slp_mean"]:
                    k = i + 1
                else:
                    break
            out.append(metric("P5", "p5_slope_monotonic_upto", int(s.loc[k - 1, "elev_cls"]),
                              "구간", zs,
                              "elev_cls 오름차순에서 slp_mean 이 엄밀 증가하는 마지막 구간",
                              "flag"))
            for cls in (1, 17):
                row = s[s["elev_cls"] == cls]
                if len(row):
                    out.append(metric("P5", "p5_zone_slope_mean_cls%d" % cls,
                                      fmt(float(row["slp_mean"].iloc[0]), 3), "도", zs,
                                      "zonalstatisticsfb slp_mean (elev_cls=%d)" % cls,
                                      "raster", True))
                else:
                    out.append(missing("P5", "p5_zone_slope_mean_cls%d" % cls, "도", zs,
                                       "raster", True))
    return out


# --- P6 ----------------------------------------------------------------------
def verify_p6(pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid])
    out = []
    pts = os.path.join(d, "00.origins", "apt_trade_suseong_5186.gpkg")
    g = read_vec(pts, layer="apt_trade")
    if g is None:
        out.append(missing("P6", "p6_point_count", "건", pts, "count"))
    else:
        out.append(metric("P6", "p6_point_count", len(g), "건", pts,
                          "geopandas 피처 수", "count"))

    raw = os.path.join(d, "00.origins", "apt_trade_suseong_raw.csv")
    if not os.path.exists(raw):
        out += [missing("P6", "p6_raw_rows", "행", raw, "count"),
                missing("P6", "p6_trade_price_mean", "만원/m2", raw, "raster"),
                missing("P6", "p6_trade_price_max", "만원/m2", raw, "raster")]
    else:
        df = pd.read_csv(raw)
        out.append(metric("P6", "p6_raw_rows", len(df), "행", raw, "pandas 행 수", "count"))
        if "price_per_m2" in df.columns:
            out.append(metric("P6", "p6_trade_price_mean", fmt(df["price_per_m2"].mean(), 3),
                              "만원/m2", raw, "원 거래 price_per_m2 평균", "raster"))
            out.append(metric("P6", "p6_trade_price_max", fmt(df["price_per_m2"].max(), 3),
                              "만원/m2", raw, "원 거래 price_per_m2 최대", "raster"))

    idw = os.path.join(d, "02.analysis", "p6_idw_price.tif")
    st = raster_stats(idw)
    if st is None:
        out += [missing("P6", "p6_idw_min", "만원/m2", idw, "raster", True),
                missing("P6", "p6_idw_max", "만원/m2", idw, "raster", True),
                missing("P6", "p6_idw_mean", "만원/m2", idw, "raster")]
    else:
        out.append(metric("P6", "p6_idw_min", fmt(st["min"], 4), "만원/m2", idw,
                          "rasterio nodata 제외 min", "raster", True))
        out.append(metric("P6", "p6_idw_max", fmt(st["max"], 4), "만원/m2", idw,
                          "rasterio nodata 제외 max", "raster", True))
        out.append(metric("P6", "p6_idw_mean", fmt(st["mean"], 4), "만원/m2", idw,
                          "rasterio nodata 제외 mean", "raster"))

    clip = os.path.join(d, "03.outputs", "p6_idw_price_suseong.tif")
    sc = raster_stats(clip)
    if sc is None:
        out += [missing("P6", "p6_idw_clip_size", "px", clip, "flag"),
                missing("P6", "p6_idw_clip_mean", "만원/m2", clip, "raster"),
                missing("P6", "p6_idw_at_region_centroid", "만원/m2", clip, "raster", True)]
    else:
        out.append(metric("P6", "p6_idw_clip_size", "%dx%d" % (sc["width"], sc["height"]),
                          "px", clip, "rasterio width/height", "flag"))
        out.append(metric("P6", "p6_idw_clip_mean", fmt(sc["mean"], 4), "만원/m2", clip,
                          "rasterio nodata 제외 mean", "raster"))
        reg = region_gdf(pid)
        if reg is None:
            out.append(missing("P6", "p6_idw_at_region_centroid", "만원/m2", clip, "raster", True))
        else:
            c = reg.geometry.union_all().centroid if hasattr(reg.geometry, "union_all") \
                else reg.geometry.unary_union.centroid
            with rasterio.open(clip) as ds:
                v = list(ds.sample([(c.x, c.y)]))[0][0]
            out.append(metric("P6", "p6_idw_at_region_centroid", fmt(float(v), 4), "만원/m2", clip,
                              "수성구 경계 centroid (%.3f, %.3f) EPSG:5186 에서 표본 추출"
                              % (c.x, c.y), "raster", True))
    return out


# --- P7 ----------------------------------------------------------------------
def verify_p7(pid):
    out = []
    # 2026-09-12: P7 은 P5 전처리본 공유 (파일명 규칙 적용본)
    dem = os.path.join(DATA_ROOT, PROJ_DIR[5], "01.preprocess", "p5_dem_wonju_5186.tif")
    if not os.path.exists(dem):
        for n, u, k, mn in [("p7_valid_cells", "셀", "count", False),
                            ("p7_low100_cells", "셀", "count", False),
                            ("p7_low100_area_km2", "km2", "area", True),
                            ("p7_low100_ratio_pct", "%", "ratio", False),
                            ("p7_area_lt80_km2", "km2", "area", True),
                            ("p7_area_80_100_km2", "km2", "area", True),
                            ("p7_area_100_120_km2", "km2", "area", True)]:
            out.append(missing("P7", n, u, dem, k, mn))
        return out

    with rasterio.open(dem) as ds:
        a = ds.read(1, masked=True)
        cell = abs(ds.res[0] * ds.res[1])
        v = a.compressed()
    total = int(v.size)
    n100 = int((v < 100).sum())
    out.append(metric("P7", "p7_valid_cells", total, "셀", dem,
                      "DEM nodata 제외 셀 수", "count"))
    out.append(metric("P7", "p7_low100_cells", n100, "셀", dem,
                      "DEM < 100 m 셀 수", "count"))
    out.append(metric("P7", "p7_low100_area_km2", fmt(n100 * cell / 1e6, 4), "km2", dem,
                      "셀 수 x %g m2 / 1e6" % cell, "area", True))
    out.append(metric("P7", "p7_low100_ratio_pct", fmt(100.0 * n100 / total, 2), "%", dem,
                      "<100 m 셀 / 유효 셀 * 100", "ratio"))
    for name, lo, hi in [("p7_area_lt80_km2", -1e9, 80.0),
                         ("p7_area_80_100_km2", 80.0, 100.0),
                         ("p7_area_100_120_km2", 100.0, 120.0)]:
        n = int(((v >= lo) & (v < hi)).sum())
        out.append(metric("P7", name, fmt(n * cell / 1e6, 4), "km2", dem,
                          "DEM %g <= z < %g 셀 수 x %g m2 / 1e6" % (lo, hi, cell),
                          "area", True))

    rep = os.path.join(DATA_ROOT, PROJ_DIR[pid], "03.outputs", "p7_risk_area.gpkg")
    gr = read_vec(rep)
    if gr is None:
        out.append(missing("P7", "p7_risk_class_area_total_km2", "km2", rep, "area"))
    else:
        out.append(metric("P7", "p7_risk_class_area_total_km2",
                          fmt(float(gr["m2"].sum()) / 1e6, 4), "km2", rep,
                          "rasterlayeruniquevaluesreport m2 합 / 1e6 (교차확인)", "area"))
    return out


# --- P8 ----------------------------------------------------------------------
def verify_p8(pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid])
    out = []
    # 2026-09-12: ① 공통 전처리 도입으로 01.preprocess 는 전국 표준입력
    # (p8_link_5186 / p8_node_5186), 전주 클립본은 ② 산출물이라 02.analysis 로 옮겼다.
    for name, fn, unit in [("p8_link_count", "p8_link_jeonju.gpkg", "개"),
                           ("p8_node_count", "p8_node_jeonju.gpkg", "개")]:
        p = os.path.join(d, "02.analysis", fn)
        g = read_vec(p)
        if g is None:
            out.append(missing("P8", name, unit, p, "count"))
        else:
            out.append(metric("P8", name, len(g), unit, p, "geopandas 피처 수", "count"))

    rp = os.path.join(d, "02.analysis", "p8_route.gpkg")
    g = read_vec(rp)
    if g is None:
        out += [missing("P8", "p8_route_length_m", "m", rp, "length", True),
                missing("P8", "p8_straight_m", "m", rp, "length"),
                missing("P8", "p8_detour_ratio", "배", rp, "ratio")]
        return out

    geom_len = float(g.geometry.length.sum())
    out.append(metric("P8", "p8_route_length_m", fmt(geom_len, 3), "m", rp,
                      "경로 지오메트리 길이 합", "length", True))
    if "cost" in g.columns:
        out.append(metric("P8", "p8_route_cost_m", fmt(float(g["cost"].iloc[0]), 3), "m", rp,
                          "shortestpath cost 속성", "length"))

    def parse_xy(s):
        m = re.findall(r"-?\d+\.?\d*", str(s))
        return (float(m[0]), float(m[1])) if len(m) >= 2 else None

    if {"start", "end"}.issubset(g.columns):
        s = parse_xy(g["start"].iloc[0])
        e = parse_xy(g["end"].iloc[0])
        if s and e:
            straight = ((s[0] - e[0]) ** 2 + (s[1] - e[1]) ** 2) ** 0.5
            out.append(metric("P8", "p8_straight_m", fmt(straight, 3), "m", rp,
                              "start/end 속성 좌표 사이 유클리드 거리", "length"))
            out.append(metric("P8", "p8_detour_ratio", fmt(geom_len / straight, 4), "배", rp,
                              "경로길이 / 직선거리", "ratio"))
            return out
    out += [missing("P8", "p8_straight_m", "m", rp, "length"),
            missing("P8", "p8_detour_ratio", "배", rp, "ratio")]
    return out


# --- P9 ----------------------------------------------------------------------
def verify_p9(pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid])
    out = []
    # 2026-09-12: lv1_1980_sejong.tif -> p9_lv1_1980_5186.tif (세종 클립본)
    clipped = os.path.join(d, "01.preprocess", "p9_lv1_1980_5186.tif")
    if not os.path.exists(clipped):
        out += [missing("P9", "p9_valid_cells", "셀", clipped, "count"),
                missing("P9", "p9_valid_area_km2", "km2", clipped, "area")]
    else:
        with rasterio.open(clipped) as ds:
            a = ds.read(1)
            nd = ds.nodata if ds.nodata is not None else 0
            cell = abs(ds.res[0] * ds.res[1])
            n = int((a != nd).sum())
        out.append(metric("P9", "p9_valid_cells", n, "셀", clipped,
                          "클립본 nodata(%g) 제외 셀 수" % nd, "count"))
        out.append(metric("P9", "p9_valid_area_km2", fmt(n * cell / 1e6, 4), "km2", clipped,
                          "셀 수 x %g m2 / 1e6" % cell, "area"))

    # 2026-09-12 4개년 재실행: 구간 3개 + 총변화. 이름에 구간을 박는다.
    for tag in ("80_90", "90_00", "00_10", "80_10"):
        code = os.path.join(d, "02.analysis", "p9_change_code_%s.tif" % tag)
        total = tag == "80_10"
        # 총변화만 기존 metric 이름을 유지한다(09-11 이래 쓰던 ID).
        m_area = "p9_change_area_km2" if total else "p9_change_%s_km2" % tag
        m_cells = "p9_change_cells" if total else "p9_change_%s_cells" % tag
        m_ratio = "p9_change_ratio_pct" if total else "p9_change_%s_pct" % tag
        m_codes = "p9_fromto_code_count" if total else "p9_fromto_%s_count" % tag
        uc = unique_counts(code)
        if uc is None:
            out += [missing("P9", m_cells, "셀", code, "count"),
                    missing("P9", m_area, "km2", code, "area", True),
                    missing("P9", m_ratio, "%", code, "ratio"),
                    missing("P9", m_codes, "종", code, "count", total)]
            continue
        v, c, cell = uc
        tot = int(c.sum())
        chg = int(c[v != 0].sum())
        out.append(metric("P9", m_cells, chg, "셀", code,
                          "from-to 코드 != 0 셀 수", "count"))
        out.append(metric("P9", m_area, fmt(chg * cell / 1e6, 4), "km2", code,
                          "변화 셀 수 x %g m2 / 1e6" % cell, "area", True))
        out.append(metric("P9", m_ratio, fmt(100.0 * chg / tot, 3), "%", code,
                          "변화 셀 / 유효 셀 * 100", "ratio"))
        out.append(metric("P9", m_codes, int((v != 0).sum()), "종", code,
                          "고유값 중 0(무변화) 제외 개수", "count", total))

    # 시가화 연대 래스터: 0 = 한 번도 시가화 아님 / 1980 = 이미 시가화 / 이후 = 처음 시가화
    uy = os.path.join(d, "02.analysis", "p9_urban_year.tif")
    uy_codes = [0, 1980, 1990, 2000, 2010]
    uc = unique_counts(uy)
    if uc is None:
        for code_v in uy_codes:
            out.append(missing("P9", "p9_urban_year_%d_km2" % code_v, "km2", uy, "area", True))
    else:
        v, c, cell = uc
        counts = dict(zip([int(round(float(x))) for x in v], [int(x) for x in c]))
        extra = sorted(set(counts) - set(uy_codes))
        if extra:
            raise SystemExit("p9_urban_year.tif 에 예상 밖 값: %r" % extra)
        for code_v in uy_codes:
            n = counts.get(code_v, 0)
            out.append(metric("P9", "p9_urban_year_%d_km2" % code_v,
                              fmt(n * cell / 1e6, 4), "km2", uy,
                              "value=%d 셀 %d x %g m2 / 1e6" % (code_v, n, cell),
                              "area", True))

    c3 = os.path.join(d, "03.outputs", "p9_change_class3_area.gpkg")
    g3 = read_vec(c3)
    labels = {0: "p9_class3_nochange_km2", 1: "p9_class3_urbanized_km2", 2: "p9_class3_other_km2"}
    if g3 is None:
        for n in labels.values():
            out.append(missing("P9", n, "km2", c3, "area", True))
    else:
        for val, name in labels.items():
            row = g3[g3["value"] == val]
            if len(row):
                out.append(metric("P9", name, fmt(float(row["m2"].iloc[0]) / 1e6, 4), "km2", c3,
                                  "rasterlayeruniquevaluesreport m2(value=%d) / 1e6" % val,
                                  "area", True))
            else:
                out.append(missing("P9", name, "km2", c3, "area", True))
    return out


# --- P10 ---------------------------------------------------------------------
def verify_p10(pid):
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid])
    out = []
    qgz = os.path.join(DATA_ROOT, "_run", "methodology_check.qgz")
    if not os.path.exists(qgz):
        out += [missing("P10", "p10_layer_count", "개", qgz, "count"),
                missing("P10", "p10_layer_vector", "개", qgz, "count"),
                missing("P10", "p10_layer_raster", "개", qgz, "count"),
                missing("P10", "p10_scalebar_scale_denom", "1:N", qgz, "raster", True),
                missing("P10", "p10_scalebar_bar_width_mm", "mm", qgz, "length")]
    else:
        with zipfile.ZipFile(qgz) as z:
            qgs = [n for n in z.namelist() if n.endswith(".qgs")][0]
            xml = z.read(qgs).decode("utf-8", "replace")
        root = ET.fromstring(xml)
        mls = root.findall(".//projectlayers/maplayer")
        cnt = Counter(m.get("type") for m in mls)
        out.append(metric("P10", "p10_layer_count", len(mls), "개", qgz,
                          "qgz 안 .qgs 의 projectlayers/maplayer 수", "count"))
        out.append(metric("P10", "p10_layer_vector", cnt.get("vector", 0), "개", qgz,
                          "maplayer type=vector", "count"))
        out.append(metric("P10", "p10_layer_raster", cnt.get("raster", 0), "개", qgz,
                          "maplayer type=raster", "count"))
        m = re.search(r'segmentMillimeters="([\d.]+)"[^>]*', xml)
        seg_mm = float(m.group(1)) if m else None
        upseg = re.search(r'numUnitsPerSegment="([\d.]+)"', xml)
        nseg = re.search(r'numSegments="(\d+)"', xml)
        unit = re.search(r'unitType="(\w+)"', xml)
        if seg_mm and upseg and unit:
            f = {"km": 1000.0, "m": 1.0}.get(unit.group(1), 1.0)
            denom = float(upseg.group(1)) * f / (seg_mm / 1000.0)
            out.append(metric("P10", "p10_scalebar_scale_denom", fmt(denom, 0), "1:N", qgz,
                              "numUnitsPerSegment(%s%s) / (segmentMillimeters %.4f mm)"
                              % (upseg.group(1), unit.group(1), seg_mm), "raster", True))
            if nseg:
                # 막대 폭(bar width)이다. 아이템 프레임 폭(size="71.9196,14,mm")과 다르다 —
                # 프레임에는 라벨·여백이 함께 들어간다. 두 값을 섞어 쓰면 안 된다.
                out.append(metric("P10", "p10_scalebar_bar_width_mm",
                                  fmt(seg_mm * int(nseg.group(1)), 2), "mm", qgz,
                                  "막대 폭 = segmentMillimeters x numSegments "
                                  "(아이템 프레임 폭 size=... 과 다름 · A4 297 mm 초과 여부 확인)",
                                  "length"))
        else:
            out.append(missing("P10", "p10_scalebar_scale_denom", "1:N", qgz, "raster", True))
            out.append(missing("P10", "p10_scalebar_bar_width_mm", "mm", qgz, "length"))

    # atlas 최신 폴더: v3 있으면 v3, 없으면 v2, 그것도 없으면 atlas
    outs = os.path.join(d, "03.outputs")
    folder = None
    for cand in ("atlas_v3", "atlas_v2", "atlas"):
        p = os.path.join(outs, cand)
        if os.path.isdir(p):
            folder = p
            break
    if folder is None:
        out += [missing("P10", "p10_atlas_page_count", "장", outs, "count", True),
                missing("P10", "p10_atlas_size_min_kb", "KB", outs, "size", True),
                missing("P10", "p10_atlas_size_max_kb", "KB", outs, "size", True)]
    else:
        files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".jpg"))
        sizes = [os.path.getsize(os.path.join(folder, f)) for f in files]
        out.append(metric("P10", "p10_atlas_folder", os.path.basename(folder), "폴더", folder,
                          "atlas_v3 > atlas_v2 > atlas 순 최신 폴더", "flag"))
        out.append(metric("P10", "p10_atlas_page_count", len(files), "장", folder,
                          "폴더 내 .jpg 개수", "count", True))
        if sizes:
            out.append(metric("P10", "p10_atlas_size_min_kb", fmt(min(sizes) / 1024.0, 1), "KB",
                              folder, "jpg 파일 크기 min / 1024", "size", True))
            out.append(metric("P10", "p10_atlas_size_max_kb", fmt(max(sizes) / 1024.0, 1), "KB",
                              folder, "jpg 파일 크기 max / 1024", "size", True))
    return out


VERIFIERS = {1: verify_p1, 2: verify_p2, 3: verify_p3, 4: verify_p4, 5: verify_p5,
             6: verify_p6, 7: verify_p7, 8: verify_p8, 9: verify_p9, 10: verify_p10}

TEMPLATE_HEADER = ["metric", "label", "mcp_value", "manual_value", "diff", "tolerance",
                   "verdict", "note"]

# metric(기계 ID) -> label(지표명). label 은 `data_projects.py` 의 `verify_metrics`
# 지표명이고, 한 지표가 여러 행으로 나뉘면 괄호로 세부를 붙인다.
# `(추가)` 로 시작하는 label 은 verify_metrics 에 없는 보조 행이다.
METRIC_LABELS = {
    # P1 verify_metrics: 후보지 수 · 후보지 면적
    "p1_candidate_count": "후보지 수",
    "p1_candidate_area_km2": "후보지 면적",
    "p1_top_count": "후보지 수(상위)",
    "p1_top_area_km2": "후보지 면적(상위)",
    # P2: 버퍼 내 상가 수
    "p2_hot_service_store_count": "버퍼 내 상가 수",
    # P3: 조인 건수 · 인구밀도 최댓값
    "p3_sido_joined_count": "조인 건수(전국 시도)",
    "p3_emd_valid_count": "조인 건수(읍면동 유효)",
    "p3_pop_dens_max": "인구밀도 최댓값",
    # P4: 소외 인구 합
    "p4_pop_underserved": "소외 인구 합",
    # P5: 표고 구간별 면적 · 평균 경사
    "p5_zone_area_sum_km2": "표고 구간별 면적(25구간 합)",
    "p5_zone_slope_mean_cls1": "평균 경사(1구간)",
    "p5_zone_slope_mean_cls17": "평균 경사(17구간)",
    # P6: 표면 최솟값 · 표면 최댓값 · 표본점 보간값
    "p6_idw_min": "표면 최솟값",
    "p6_idw_max": "표면 최댓값",
    "p6_idw_at_region_centroid": "표본점 보간값",
    # P7: 침수 위험 면적
    "p7_low100_area_km2": "침수 위험 면적(<100 m)",
    "p7_area_lt80_km2": "침수 위험 면적(<80 m)",
    "p7_area_80_100_km2": "침수 위험 면적(80~100 m)",
    "p7_area_100_120_km2": "침수 위험 면적(100~120 m)",
    # P8: 최단경로 거리
    "p8_route_length_m": "최단경로 거리",
    # P9: 구간별 변화 면적 · 시가화 연대별 면적 (2026-09-12 4개년 구조)
    "p9_change_80_90_km2": "구간별 변화 면적(1980→1990)",
    "p9_change_90_00_km2": "구간별 변화 면적(1990→2000)",
    "p9_change_00_10_km2": "구간별 변화 면적(2000→2010)",
    "p9_change_area_km2": "구간별 변화 면적(총변화 1980→2010)",
    "p9_urban_year_0_km2": "시가화 연대별 면적(한 번도 아님)",
    "p9_urban_year_1980_km2": "시가화 연대별 면적(1980 이미 시가화)",
    "p9_urban_year_1990_km2": "시가화 연대별 면적(1990 처음)",
    "p9_urban_year_2000_km2": "시가화 연대별 면적(2000 처음)",
    "p9_urban_year_2010_km2": "시가화 연대별 면적(2010 처음)",
    "p9_class3_nochange_km2": "(추가) 총변화 3분류 면적(무변화)",
    "p9_class3_urbanized_km2": "(추가) 총변화 3분류 면적(시가화 전환)",
    "p9_class3_other_km2": "(추가) 총변화 3분류 면적(기타 변화)",
    "p9_fromto_code_count": "(추가) from-to 전이 코드 종수(총변화)",
    # P10: Atlas 페이지 수 · 용량 범위 · 축척(축척바 역산)
    "p10_atlas_page_count": "Atlas 페이지 수",
    "p10_atlas_size_min_kb": "용량 범위(최소)",
    "p10_atlas_size_max_kb": "용량 범위(최대)",
    "p10_scalebar_scale_denom": "축척(축척바 역산)",
}


def write_template(pid, metrics):
    """projNN\\04.verify\\verify_pN.csv 생성 (manual=True 지표만).

    `metric` 은 기계 ID, `label` 이 지표명이다. `verify_metrics` 의 한 지표가
    여기서 여러 세부 행으로 나뉜다(1:N). label 이 비면 METRIC_LABELS 에 등록이
    빠진 것이므로 경고를 찍는다.
    """
    d = os.path.join(DATA_ROOT, PROJ_DIR[pid], "04.verify")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "verify_p%d.csv" % pid)
    rows = [m for m in metrics if m["manual"]]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(TEMPLATE_HEADER)
        f.flush()
        for m in rows:
            note = "%s | %s" % (m["source_file"], m["method"])
            label = METRIC_LABELS.get(m["metric"], "")
            if not label:
                print("  [WARN] label 미등록 metric: %s" % m["metric"])
            w.writerow([m["metric"], label, m["value"], "", "",
                        TOL.get(m["kind"], ""), "", note])
            f.flush()
    return path, len(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description="산출 파일에서 핵심 수치 재계산")
    ap.add_argument("--projects", default="1,2,3,4,5,6,7,8,9,10",
                    help="대상 프로젝트 번호 (예: 2,3). 기본 전체")
    ap.add_argument("--template", action="store_true",
                    help="projNN/04.verify/verify_pN.csv 수동 검증 템플릿도 생성")
    ap.add_argument("--log", default=None, help="로그 파일 경로 지정(기본 verify_YYMMDD.csv)")
    args = ap.parse_args(argv)

    pids = []
    for tok in args.projects.split(","):
        tok = tok.strip()
        if tok:
            pids.append(int(tok))

    log = Log(args.log)
    print("[LOG] %s" % log.path)
    made = []
    try:
        for pid in pids:
            if pid not in VERIFIERS:
                print("  skip unknown project %s" % pid)
                continue
            metrics = VERIFIERS[pid](pid)
            for m in metrics:
                log.write(m)
                print("  %-4s %-32s %-18s %s" % (m["project"], m["metric"],
                                                 str(m["value"]), m["method"]))
            if args.template:
                path, n = write_template(pid, metrics)
                made.append((path, n))
                print("  -> template %s (%d rows)" % (path, n))
    finally:
        log.close()

    if made:
        print("\n생성한 템플릿 %d개" % len(made))
        for p, n in made:
            print("  %s  %d rows" % (p, n))
    print("\n로그: %s" % log.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
