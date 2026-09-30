<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<!--
  토지피복지도 대분류 래스터 표준 스타일 (P9)

  대상: proj09_landcover/01.preprocess/p9_lv1_YYYY_5186.tif (EPSG:5186, 30 m, uint8)
  셀 값: 1~7. nodata 0 (레이어 nodata 설정으로 투명 처리된다)

  색: 환경부 「토지피복지도 작성지침」 [별표 1] 토지피복지도 분류코드 및 색상표준
      <대분류 토지피복지도 분류체계> 의 R/G/B 값 그대로다. 관례색이 아니다.
      원문 PDF: https://www.law.go.kr/LSW/flDownload.do?flSeq=158209827
      국가법령정보센터(law.go.kr) 행정규칙 「토지피복지도 작성지침」 별표 1
      원문에 hex 표기는 없다. 아래 hex 는 원문 R/G/B 를 그대로 변환한 값이다.

  값 체계 주의: 별표 1 의 대분류 코드는 100 단위(100~700)다. 그런데 이 강의가 쓰는
      EGIS WCS 산출 래스터의 셀 값은 1~7 이다(2026-09-30 실측: 원본 4장·전처리본 4장 모두
      고유값이 1~7, 100 단위 값은 한 칸도 없다). 그래서 팔레트 값은 1~7 로 두었다.
      값 N 이 별표 1 의 코드 N00 에 대응한다는 것은 handouts/DATA_MANIFEST.md 의
      "대분류 코드 | 1 시가화·건조 · 2 농업 · 3 산림 · 4 초지 · 5 습지 · 6 나지 · 7 수역" 에 따른다.

  출처 표시: 토지피복지도 대분류, 환경부 환경공간정보서비스(EGIS), https://egis.me.go.kr
      (공공누리 제1유형, 출처 표시 의무). 이 스타일로 만든 도면에도 출처 표시가 따라간다.
-->
<qgis version="3.44.14-Solothurn" styleCategories="Symbology">
  <pipe>
    <rasterrenderer type="paletted" band="1" opacity="1" alphaBand="-1" nodataColor="">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <colorPalette>
        <paletteEntry value="1" color="#ff0000" label="시가화건조지역" alpha="255"/>
        <paletteEntry value="2" color="#eee907" label="농업지역" alpha="255"/>
        <paletteEntry value="3" color="#2a4b2d" label="산림지역" alpha="255"/>
        <paletteEntry value="4" color="#399626" label="초지" alpha="255"/>
        <paletteEntry value="5" color="#7c227e" label="습지" alpha="255"/>
        <paletteEntry value="6" color="#59ceca" label="나지" alpha="255"/>
        <paletteEntry value="7" color="#0602fa" label="수역" alpha="255"/>
      </colorPalette>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
    <huesaturation colorizeGreen="128" colorizeStrength="100" colorizeRed="255" colorizeOn="0" grayscaleMode="0" saturation="0" invertColors="0" colorizeBlue="128"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
</qgis>
