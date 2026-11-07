"""Write site/data/notes.json (captions per date and the "About the data" text)
from site/data/stats.json and scripts/roads_2012_2013_by_source.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = json.loads((ROOT / "site/data/stats.json").read_text())
SRC = json.loads((ROOT / "scripts/roads_2012_2013_by_source.json").read_text())
ts = S["timestamps"]
km = dict(zip(ts, S["roadKm"]))
bl = dict(zip(ts, S["buildings"]))
us = dict(zip(ts, S["users"]))
latest = ts[-1]


def n(v):
    return f"{round(v):,}"


y12, y13 = SRC["2012"], SRC["2013"]
k12, k13 = y12["byKind"], y13["byKind"]
share13 = k13["yahoo_alps_import"]["ways"] / y13["waysAdded"] * 100

# share of buildings added in 2018 that lie within 15 km of central Obihiro (grid cells)
_grid = json.loads((ROOT / "site/data/buildings.json").read_text())["rows"]
_k = ts.index("2019-01-01")
_add = [(x, y, c[_k] - c[_k - 1]) for x, y, c in _grid]
_near = sum(d for x, y, d in _add if ((x - 143.196) * 81) ** 2 + ((y - 42.924) * 111) ** 2 < 15 ** 2)
near_share = round(_near / sum(d for _, _, d in _add) * 10)

WIKI = '<a href="https://wiki.openstreetmap.org/wiki/YahooJapanALPS_Data" target="_blank" rel="noopener">OSM Wiki: YahooJapanALPS Data</a>'

frames = {
    "2008-01-01": {
        "en": "A blank sheet. On this date OpenStreetMap had not a single road in Tokachi.",
        "ja": "白紙。この日、OpenStreetMap の十勝には、まだ道路が1本もありませんでした。",
    },
    "2010-01-01": {
        "en": f"The first {n(km['2010-01-01'])} km of roads. {n(us['2010-01-01'])} people edited here in 2009.",
        "ja": f"最初の {n(km['2010-01-01'])} km。2009年にここを編集した人は {n(us['2010-01-01'])} 人でした。",
    },
    "2013-01-01": {
        "en": (f"In 2012 the roads grew from {n(km['2012-01-01'])} km to {n(km['2013-01-01'])} km. "
               f"Of the {n(y12['waysAdded'])} road lines added, {n(k12['bing_imagery']['ways'])} came from edits "
               f"whose comment says they were traced from Bing aerial imagery, and {n(k12['yahoo_alps_import']['ways'])} "
               "from imports of Yahoo! JAPAN / ALPS road data."),
        "ja": (f"2012年、道路は {n(km['2012-01-01'])} km から {n(km['2013-01-01'])} km に。"
               f"この年に追加された {n(y12['waysAdded'])} 本のうち、{n(k12['bing_imagery']['ways'])} 本は"
               f"「Bing の航空写真から描いた」とコメントのある編集、{n(k12['yahoo_alps_import']['ways'])} 本は"
               "Yahoo! JAPAN / ALPS の道路データの取り込み（インポート）によるものでした。"),
        "source": {"en": "Source: changeset comments (OSM API)", "ja": "根拠：変更セットのコメント（OSM API）"},
    },
    "2014-01-01": {
        "en": (f"In 2013 the roads tripled, to {n(km['2014-01-01'])} km. "
               f"{n(k13['yahoo_alps_import']['ways'])} of the {n(y13['waysAdded'])} road lines added ({share13:.1f}%) "
               "were imports of road data that Yahoo! JAPAN released to OpenStreetMap Foundation Japan in 2011 "
               "(ALPS map data based on GSI 1:25,000 maps). Volunteers imported it one town at a time: "
               "Memuro, Obihiro, Makubetsu, Urahoro, Otofuke, and more."),
        "ja": (f"2013年、道路は3倍の {n(km['2014-01-01'])} km に。"
               f"追加された {n(y13['waysAdded'])} 本のうち {n(k13['yahoo_alps_import']['ways'])} 本（{share13:.1f}%）は、"
               "Yahoo! JAPAN が2011年に OpenStreetMap Foundation Japan へ提供した道路データ"
               "（国土地理院の数値地図25000を基にした ALPS の地図データ）の取り込みでした。"
               "芽室町、帯広市、幕別町、浦幌町、音更町…と、ボランティアが市町村ごとに取り込んでいます。"),
        "source": {"en": f"Sources: changeset comments (OSM API); {WIKI}",
                   "ja": f"根拠：変更セットのコメント（OSM API）、{WIKI}"},
    },
    "2018-01-01": {
        "en": f"Buildings start to fill in: {n(bl['2017-01-01'])} a year ago, {n(bl['2018-01-01'])} now.",
        "ja": f"建物が描かれ始めます。1年前は {n(bl['2017-01-01'])} 棟、この日は {n(bl['2018-01-01'])} 棟。",
    },
    "2019-01-01": {
        "en": (f"{n(bl['2019-01-01'] - bl['2018-01-01'])} buildings added in one year, "
               f"about {near_share} in 10 of them within 15 km of central Obihiro."),
        "ja": (f"1年で {n(bl['2019-01-01'] - bl['2018-01-01'])} 棟が追加されました。"
               f"およそ10棟に{near_share}棟は、帯広の中心から15km以内です。"),
    },
    latest: {
        "en": (f"Today: {n(km[latest])} km of roads and {n(bl[latest])} buildings. "
               "The map is never finished: roads, buildings, fields and woods are still being added every year."),
        "ja": (f"いま：道路 {n(km[latest])} km、建物 {n(bl[latest])} 棟。"
               "地図に完成はありません。道路も建物も畑も林も、毎年描き足されています。"),
    },
}

about = {
    "en": f"""<p>All figures come from the <a href="https://api.ohsome.org/" target="_blank" rel="noopener">ohsome API</a> (HeiGIT), which keeps the full editing history of OpenStreetMap. They show what had been drawn in OSM at each date, as stored in the ohsome database (data up to {latest}), not what exists on the ground.</p>
<p><b>Area</b>: Tokachi Subprefecture, using the outline from MLIT National Land Numerical Information (administrative areas N03, 2024), slightly simplified. <b>Dates</b>: 1 January of each year from 2008 to 2026, and {latest}, the latest date available.</p>
<p><b>Roads</b>: ways tagged highway=*. <b>Buildings</b>: building=* areas; on the map they are counted in cells of about 2 km. <b>Farmland</b>: landuse=farmland, meadow or orchard. <b>Woods &amp; windbreaks</b>: landuse=forest, natural=wood and natural=tree_row. <b>People who edited</b>: accounts that changed at least one way (road, building, land use, river…) in the area during the 12 months before each date. Only the number is shown, never names.</p>
<p>Each feature is drawn with its latest shape, from the first date it existed. Orange marks features that first appeared in the 12 months before the date shown.</p>
<p>Map data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> (ODbL) · ohsome by HeiGIT · National Land Numerical Information N03 (MLIT) · Method and code: <a href="https://github.com/shinyanakashima/30daymapchallenge-2026day21-who-mapped-tokachi" target="_blank" rel="noopener">GitHub</a></p>""",
    "ja": f"""<p>数値はすべて、OpenStreetMap の編集履歴を持つ <a href="https://api.ohsome.org/" target="_blank" rel="noopener">ohsome API</a>（HeiGIT）で集計したものです。各時点で OSM に描かれていたものを、ohsome のデータベース（{latest} までのデータ）に基づいて示しています。現地に実際にあるものの数ではありません。</p>
<p><b>範囲</b>：十勝総合振興局の管内（国土数値情報 行政区域 N03・2024年の形を少し簡略化）。<b>時点</b>：2008〜2026年の各年1月1日と、データのある最新の {latest}。</p>
<p><b>道路</b>：highway=* のウェイ。<b>建物</b>：building=* の面。地図では約2km四方ごとに数えています。<b>農地</b>：landuse=farmland・meadow・orchard。<b>林・防風林</b>：landuse=forest、natural=wood、natural=tree_row。<b>編集した人</b>：各時点までの1年間に、範囲内のウェイ（道路、建物、土地利用、川など）を1つ以上編集したアカウントの数。人数だけを示し、名前は出していません。</p>
<p>形は各地物の最新のもので、最初に現れた時点から表示しています。オレンジは、その日までの1年間に初めて現れたものです。</p>
<p>地図データ © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>（ODbL）・ohsome by HeiGIT・国土数値情報（行政区域 N03、国土交通省）・方法とコード：<a href="https://github.com/shinyanakashima/30daymapchallenge-2026day21-who-mapped-tokachi" target="_blank" rel="noopener">GitHub</a></p>""",
}

(ROOT / "site/data/notes.json").write_text(json.dumps({"frames": frames, "about": about}, ensure_ascii=False))
print("ok")
