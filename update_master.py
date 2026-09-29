#!/usr/bin/env python3
import argparse, json, re, time, gzip, html
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import xml.etree.ElementTree as ET

API = "https://iptv-org.github.io/api"
UA = "MasterTV/2.0 (+personal-use public-stream playlist builder)"
TIMEOUT = 25

GROUP_SECTIONS = [
    ("LIBRARY", ["⭐ FAVORITES", "🕘 RECENTLY WATCHED"]),
    ("🌎 COUNTRIES / REGIONS", [
        "🇵🇷 PUERTO RICO", "🇺🇸 USA | ENGLISH", "🇺🇸 USA | SPANISH", "🇨🇴 COLOMBIA", "🇲🇽 MEXICO",
        "🇩🇴 DOMINICAN REPUBLIC", "🇪🇸 SPAIN", "🇦🇷 ARGENTINA", "🇨🇱 CHILE", "🇵🇪 PERU", "🇻🇪 VENEZUELA",
        "🇪🇨 ECUADOR", "🇵🇦 PANAMA", "🇨🇷 COSTA RICA", "🇬🇹 GUATEMALA", "🇸🇻 EL SALVADOR", "🇭🇳 HONDURAS",
        "🇺🇾 URUGUAY", "🇧🇷 BRAZIL", "🌎 LATINOAMERICA", "🇬🇧 UK", "🇨🇦 CANADA", "🇫🇷 FRANCE", "🇮🇹 ITALY",
        "🇩🇪 GERMANY", "🌍 INTERNATIONAL"
    ]),
    ("🏆 SPORTS", [
        "🏆 SPORTS", "🏈 NFL / FOOTBALL", "⚾ MLB / BASEBALL", "🏀 NBA / BASKETBALL", "🏒 NHL / HOCKEY",
        "⚽ SOCCER / FÚTBOL", "🎾 TENNIS", "🥊 BOXING", "🥋 MMA / COMBAT SPORTS", "🏎 F1 / MOTORSPORTS",
        "🏁 MOTORSPORTS OTHER", "🏌️ GOLF", "🏐 OTHER SPORTS", "🏆 SPORTS NEWS"
    ]),
    ("📺 ENTERTAINMENT", [
        "📺 ENTERTAINMENT", "🎬 MOVIES", "🎞 CLASSIC MOVIES", "😂 COMEDY", "🎭 DRAMA", "🔪 ACTION", "👻 HORROR",
        "💕 ROMANCE", "🤠 WESTERN", "🚀 SCI-FI", "📺 SERIES", "⭐ GENERAL ENTERTAINMENT"
    ]),
    ("👶 KIDS", ["👶 KIDS", "🎨 CARTOONS / ANIMATION", "🧸 PRESCHOOL", "👨‍👩‍👧 FAMILY"]),
    ("📰 NEWS", ["📰 NEWS", "🇺🇸 USA NEWS", "🌎 LATINO NEWS", "🌍 INTERNATIONAL NEWS", "💰 BUSINESS NEWS", "🌦 WEATHER"]),
    ("📚 KNOWLEDGE", ["📚 KNOWLEDGE", "🌎 DOCUMENTARIES", "🔬 SCIENCE", "🌿 NATURE", "🏛 HISTORY", "✈️ TRAVEL", "🍳 COOKING", "🚗 AUTOMOTIVE"]),
    ("🎵 MUSIC", ["🎵 MUSIC", "🎤 LATIN MUSIC", "🎸 ROCK / POP", "🎶 MUSIC VIDEOS", "📻 RADIO"]),
    ("🙏 RELIGIOUS", ["🙏 RELIGIOUS", "✝️ CHRISTIAN", "⛪ CATHOLIC", "🌍 OTHER RELIGIOUS"]),
    ("📡 LOCAL TV", ["📡 LOCAL TV", "🇵🇷 PUERTO RICO LOCAL", "🇺🇸 USA LOCAL", "🇨🇴 COLOMBIA LOCAL", "🌎 LATAM LOCAL"]),
    ("🎟 EVENTS", ["🎟 EVENTS", "📺 SPECIAL EVENTS", "🏆 SPORTS EVENTS"]),
]

GROUP_ORDER = [g for _, groups in GROUP_SECTIONS for g in groups]
VIRTUAL_GROUPS = {"⭐ FAVORITES", "🕘 RECENTLY WATCHED"}

CATEGORY_MAP = {
    "sports": ["🏆 SPORTS"], "sport": ["🏆 SPORTS"],
    "movies": ["🎬 MOVIES"], "movie": ["🎬 MOVIES"], "classic": ["🎞 CLASSIC MOVIES"],
    "comedy": ["😂 COMEDY"], "series": ["📺 SERIES"], "entertainment": ["📺 ENTERTAINMENT"], "general": ["⭐ GENERAL ENTERTAINMENT"],
    "kids": ["👶 KIDS"], "children": ["👶 KIDS"], "animation": ["🎨 CARTOONS / ANIMATION"], "family": ["👨‍👩‍👧 FAMILY"],
    "news": ["📰 NEWS"], "business": ["💰 BUSINESS NEWS"], "weather": ["🌦 WEATHER"],
    "documentary": ["📚 KNOWLEDGE", "🌎 DOCUMENTARIES"], "science": ["📚 KNOWLEDGE", "🔬 SCIENCE"], "travel": ["📚 KNOWLEDGE", "✈️ TRAVEL"],
    "cooking": ["📚 KNOWLEDGE", "🍳 COOKING"], "auto": ["📚 KNOWLEDGE", "🚗 AUTOMOTIVE"],
    "music": ["🎵 MUSIC"], "religious": ["🙏 RELIGIOUS"]
}

KEYWORDS = {
    "🏈 NFL / FOOTBALL": ["nfl", "american football", "football network"],
    "⚾ MLB / BASEBALL": ["mlb", "baseball", "beisbol", "béisbol"],
    "🏀 NBA / BASKETBALL": ["nba", "basketball", "baloncesto", "basket"],
    "🏒 NHL / HOCKEY": ["nhl", "hockey"],
    "⚽ SOCCER / FÚTBOL": ["soccer", "futbol", "fútbol", "premier league", "laliga", "la liga", "champions league", "uefa", "fifa"],
    "🎾 TENNIS": ["tennis", "atp", "wta"],
    "🥊 BOXING": ["boxing", "boxeo"],
    "🥋 MMA / COMBAT SPORTS": ["mma", "ufc", "combat", "fight", "wrestling", "lucha", "martial arts"],
    "🏎 F1 / MOTORSPORTS": ["formula 1", "formula one", "f1", "motogp"],
    "🏁 MOTORSPORTS OTHER": ["nascar", "indycar", "motorsport", "racing", "rally"],
    "🏌️ GOLF": ["golf", "pga"],
    "🏆 SPORTS NEWS": ["sports news", "sport news", "espn news"],
    "🎞 CLASSIC MOVIES": ["classic movie", "classic cinema", "old movies", "golden age"],
    "🎭 DRAMA": ["drama"], "🔪 ACTION": ["action"], "👻 HORROR": ["horror", "terror"], "💕 ROMANCE": ["romance", "romantic"],
    "🤠 WESTERN": ["western"], "🚀 SCI-FI": ["sci-fi", "science fiction", "scifi"],
    "🧸 PRESCHOOL": ["preschool", "pre-school", "toddler", "baby tv", "babytv"],
    "🌿 NATURE": ["nature", "wildlife", "animal", "earth"], "🏛 HISTORY": ["history", "historia"],
    "🎤 LATIN MUSIC": ["latin music", "latino music", "reggaeton", "salsa", "bachata", "merengue"],
    "🎸 ROCK / POP": ["rock", "pop music", "hits"], "🎶 MUSIC VIDEOS": ["music video", "videos musicales", "vevo", "mtv"],
    "📻 RADIO": ["radio", "fm ", "am "],
    "✝️ CHRISTIAN": ["christian", "cristian", "evangel", "gospel"], "⛪ CATHOLIC": ["catholic", "catolic", "ewtn"],
    "🎟 EVENTS": ["event channel", "events channel", "special event", "live event"],
    "📺 SPECIAL EVENTS": ["special event", "special events", "event tv"],
    "🏆 SPORTS EVENTS": ["sports event", "sport event", "live sports event"],
}


def get_json(session, name, cache_dir: Path, max_age=6*3600):
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / name
    if p.exists() and time.time() - p.stat().st_mtime < max_age:
        return json.loads(p.read_text(encoding="utf-8"))
    r = session.get(f"{API}/{name}", timeout=TIMEOUT)
    r.raise_for_status(); p.write_bytes(r.content); return r.json()


def quality_rank(q):
    if not q: return 0
    m = re.search(r"(\d{3,4})", str(q)); return int(m.group(1)) if m else 0


def clean_name(s):
    s = re.sub(r"\s*\((?:\d{3,4}p|Geo-blocked|Not 24/7|SD|HD|FHD|UHD)\)\s*", " ", s or "", flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def pick_logo(logos):
    if not logos: return ""
    arr = [x for x in logos if x.get("in_use")] or logos
    arr = sorted(arr, key=lambda x: ("horizontal" in (x.get("tags") or []), x.get("width") or 0), reverse=True)
    return arr[0].get("url") or ""


def langs_for(channel_id, feed_id, feeds_by_key, guides_by_channel):
    out=[]
    if feed_id:
        f=feeds_by_key.get((channel_id,feed_id)); out.extend((f or {}).get("languages") or [])
    for g in guides_by_channel.get(channel_id,[]):
        if g.get("lang")=="es": out.append("spa")
        elif g.get("lang")=="en": out.append("eng")
    return list(dict.fromkeys(out))


def channel_blob(ch, st):
    cats=" ".join(str(c).lower() for c in (ch.get("categories") or []))
    return " ".join([ch.get("name") or "", st.get("title") or "", cats]).lower()


def is_local(ch, blob):
    # IPTV-org often uses city/state/region-oriented names for local broadcast channels.
    return any(x in blob for x in [" local", "local ", "regional", "municipal", "city tv", "canal local", "televisión local", "television local"])


def groups_for(ch, st, cfg, langs):
    country=ch.get("country") or ""; groups=[]
    # Country / region
    if country=="US":
        if "spa" in langs and "eng" not in langs: groups.append("🇺🇸 USA | SPANISH")
        elif "spa" in langs: groups.extend(["🇺🇸 USA | ENGLISH", "🇺🇸 USA | SPANISH"])
        else: groups.append("🇺🇸 USA | ENGLISH")
    elif country in cfg["country_groups"]: groups.append(cfg["country_groups"][country])
    elif country in cfg["latam_countries"]: groups.append("🌎 LATINOAMERICA")
    else: groups.append("🌍 INTERNATIONAL")
    if cfg.get("duplicate_into_latam") and country in cfg["latam_countries"] and "🌎 LATINOAMERICA" not in groups: groups.append("🌎 LATINOAMERICA")

    if cfg.get("duplicate_into_content_groups"):
        cats=[str(c).lower() for c in (ch.get("categories") or [])]
        for c in cats:
            groups.extend(CATEGORY_MAP.get(c,[]))
        blob=channel_blob(ch,st)
        for group,kws in KEYWORDS.items():
            if any(k in blob for k in kws): groups.append(group)
        if "🏆 SPORTS" in groups:
            specific={"🏈 NFL / FOOTBALL","⚾ MLB / BASEBALL","🏀 NBA / BASKETBALL","🏒 NHL / HOCKEY","⚽ SOCCER / FÚTBOL","🎾 TENNIS","🥊 BOXING","🥋 MMA / COMBAT SPORTS","🏎 F1 / MOTORSPORTS","🏁 MOTORSPORTS OTHER","🏌️ GOLF","🏆 SPORTS NEWS"}
            if not specific.intersection(groups): groups.append("🏐 OTHER SPORTS")
        if "📰 NEWS" in groups:
            if country=="US": groups.append("🇺🇸 USA NEWS")
            elif country in cfg["latam_countries"]: groups.append("🌎 LATINO NEWS")
            else: groups.append("🌍 INTERNATIONAL NEWS")
        if "🎵 MUSIC" in groups and country in cfg["latam_countries"]: groups.append("🎤 LATIN MUSIC")
        if "🙏 RELIGIOUS" in groups and not any(g in groups for g in ["✝️ CHRISTIAN","⛪ CATHOLIC"]): groups.append("🌍 OTHER RELIGIOUS")
        if is_local(ch,blob):
            groups.append("📡 LOCAL TV")
            if country=="PR": groups.append("🇵🇷 PUERTO RICO LOCAL")
            elif country=="US": groups.append("🇺🇸 USA LOCAL")
            elif country=="CO": groups.append("🇨🇴 COLOMBIA LOCAL")
            elif country in cfg["latam_countries"]: groups.append("🌎 LATAM LOCAL")
        # Event streams remain strictly metadata/title-driven. No unauthorized PPV sources are added.
        if any(g in groups for g in ["📺 SPECIAL EVENTS","🏆 SPORTS EVENTS"]): groups.append("🎟 EVENTS")
        if "🏆 SPORTS EVENTS" in groups and "🏆 SPORTS" not in groups: groups.append("🏆 SPORTS")
    return list(dict.fromkeys(groups))


def xmltv_dt(dt): return dt.strftime("%Y%m%d%H%M%S +0000")


def build_fallback_epg(entries,cfg,out_path):
    root=ET.Element("tv",{"generator-info-name":"MasterTV V2"}); seen=set()
    for e in entries:
        cid=e["tvg_id"]
        if cid in seen: continue
        seen.add(cid); ce=ET.SubElement(root,"channel",{"id":cid}); ET.SubElement(ce,"display-name").text=e["name"]
        if e.get("logo"): ET.SubElement(ce,"icon",{"src":e["logo"]})
    start=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0); hours=int(cfg.get("fallback_epg_hours",72)); block=6
    title=cfg.get("fallback_program_title","Live programming — schedule unavailable")
    for e in {x["tvg_id"]:x for x in entries}.values():
        for i in range(0,hours,block):
            st=start+timedelta(hours=i); en=min(start+timedelta(hours=i+block),start+timedelta(hours=hours))
            pe=ET.SubElement(root,"programme",{"start":xmltv_dt(st),"stop":xmltv_dt(en),"channel":e["tvg_id"]})
            ET.SubElement(pe,"title",{"lang":"en"}).text=title
            ET.SubElement(pe,"desc",{"lang":"en"}).text="MasterTV fallback EPG: reliable programme-level guide data was unavailable for this channel at build time."
    ET.ElementTree(root).write(out_path,encoding="utf-8",xml_declaration=True)


def try_merge_real_epg(session,entries,guides_by_channel,fallback_path,out_path,max_sources=100):
    wanted={e["tvg_id"] for e in entries}; sources=[]
    for cid in wanted:
        for g in guides_by_channel.get(cid,[]):
            for s in g.get("sources") or []:
                u=s.get("url")
                if u and u not in sources: sources.append(u)
    sources=sources[:max_sources]; base=ET.parse(fallback_path).getroot(); channel_seen={x.attrib.get("id") for x in base.findall("channel")}; real=set()
    for u in sources:
        try:
            r=session.get(u,timeout=15)
            if r.status_code!=200 or len(r.content)>50_000_000: continue
            data=r.content
            if u.endswith(".gz") or data[:2]==b"\x1f\x8b": data=gzip.decompress(data)
            root=ET.fromstring(data)
            for ce in root.findall("channel"):
                cid=ce.attrib.get("id")
                if cid in wanted and cid not in channel_seen: base.append(ce); channel_seen.add(cid)
            for pe in root.findall("programme"):
                cid=pe.attrib.get("channel")
                if cid in wanted: base.append(pe); real.add(cid)
        except Exception: continue
    for pe in list(base.findall("programme")):
        cid=pe.attrib.get("channel"); title=pe.findtext("title") or ""
        if cid in real and title.startswith("Live programming"): base.remove(pe)
    ET.ElementTree(base).write(out_path,encoding="utf-8",xml_declaration=True)
    return len(real),len(sources)


def parse_xmltv_time(s):
    if not s: return None
    try: return datetime.strptime(s[:14],"%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except Exception: return None


def build_epg_index(epg_path,out_path):
    now=datetime.now(timezone.utc); root=ET.parse(epg_path).getroot(); by=defaultdict(list)
    for p in root.findall("programme"):
        st=parse_xmltv_time(p.attrib.get("start")); en=parse_xmltv_time(p.attrib.get("stop")); cid=p.attrib.get("channel")
        if not cid or not st or not en: continue
        if en < now-timedelta(hours=1) or st > now+timedelta(hours=24): continue
        by[cid].append((st,en,p.findtext("title") or "",p.findtext("desc") or ""))
    idx={}
    for cid,arr in by.items():
        arr.sort(key=lambda x:x[0]); current=None; nxt=None
        for item in arr:
            if item[0] <= now < item[1]: current=item
            elif item[0] > now and nxt is None: nxt=item
        def pack(x):
            return None if not x else {"start":x[0].isoformat(),"stop":x[1].isoformat(),"title":x[2],"desc":x[3]}
        idx[cid]={"now":pack(current),"next":pack(nxt)}
    out_path.write_text(json.dumps(idx,ensure_ascii=False,separators=(",",":")),encoding="utf-8")


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="config.json"); ap.add_argument("--out",default="output"); ap.add_argument("--real-epg",action="store_true"); ap.add_argument("--max-epg-sources",type=int,default=100); args=ap.parse_args()
    root=Path(__file__).resolve().parent; cfg=json.loads((root/args.config).read_text(encoding="utf-8")); out=root/args.out; out.mkdir(parents=True,exist_ok=True); cache=root/".cache"
    s=requests.Session(); s.headers.update({"User-Agent":UA})
    channels=get_json(s,"channels.json",cache); feeds=get_json(s,"feeds.json",cache); logos=get_json(s,"logos.json",cache); streams=get_json(s,"streams.json",cache); guides=get_json(s,"guides.json",cache); blocklist=get_json(s,"blocklist.json",cache)
    ch_by_id={x["id"]:x for x in channels}; feeds_by_key={(x.get("channel"),x.get("id")):x for x in feeds}; logos_by_channel=defaultdict(list); guides_by_channel=defaultdict(list)
    for x in logos: logos_by_channel[x.get("channel")].append(x)
    for x in guides:
        if x.get("channel"): guides_by_channel[x["channel"]].append(x)
    blocked={x.get("channel") for x in blocklist} if cfg.get("exclude_blocklisted") else set(); candidate=defaultdict(list)
    for st in streams:
        cid=st.get("channel")
        if not cid or cid not in ch_by_id or not st.get("url"): continue
        ch=ch_by_id[cid]
        if cfg.get("exclude_nsfw") and ch.get("is_nsfw"): continue
        if cid in blocked: continue
        candidate[(cid,st.get("feed"))].append(st)
    best=[]
    for _,arr in candidate.items():
        arr.sort(key=lambda x:(quality_rank(x.get("quality")),"Geo-blocked" not in (x.get("labels") or [])),reverse=True); best.append(arr[0])
    base=[]; intl_count=0
    for st in best:
        cid=st["channel"]; ch=ch_by_id[cid]; langs=langs_for(cid,st.get("feed"),feeds_by_key,guides_by_channel); groups=groups_for(ch,st,cfg,langs)
        if groups==["🌍 INTERNATIONAL"]:
            if intl_count>=int(cfg.get("international_limit",4000)): continue
            intl_count+=1
        base.append({"tvg_id":cid,"name":clean_name(st.get("title") or ch.get("name") or cid),"url":st["url"],"logo":pick_logo(logos_by_channel.get(cid,[])),"groups":groups,"country":ch.get("country") or "","languages":langs,"quality":st.get("quality") or "","labels":st.get("labels") or [],"referrer":st.get("referrer"),"user_agent":st.get("user_agent"),"has_guide_metadata":bool(guides_by_channel.get(cid))})
    order={g:i for i,g in enumerate(GROUP_ORDER)}; expanded=[]
    for e in base:
        for g in e["groups"]:
            if g in VIRTUAL_GROUPS: continue
            x=dict(e); x["group"]=g; expanded.append(x)
    expanded.sort(key=lambda e:(order.get(e["group"],999),e["name"].lower(),e["tvg_id"]))
    with (out/"master.m3u").open("w",encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="epg.xml"\n')
        for e in expanded:
            attrs=[f'tvg-id="{e["tvg_id"]}"',f'tvg-name="{html.escape(e["name"],quote=True)}"',f'group-title="{html.escape(e["group"],quote=True)}"']
            if e.get("logo"): attrs.append(f'tvg-logo="{html.escape(e["logo"],quote=True)}"')
            f.write('#EXTINF:-1 '+' '.join(attrs)+','+e['name']+'\n')
            if e.get("referrer"): f.write(f'#EXTVLCOPT:http-referrer={e["referrer"]}\n')
            if e.get("user_agent"): f.write(f'#EXTVLCOPT:http-user-agent={e["user_agent"]}\n')
            f.write(e['url']+'\n')
    (out/"channels.json").write_text(json.dumps(base,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (out/"groups.json").write_text(json.dumps(GROUP_ORDER,ensure_ascii=False),encoding="utf-8")
    (out/"group_sections.json").write_text(json.dumps([{"title":t,"groups":g} for t,g in GROUP_SECTIONS],ensure_ascii=False),encoding="utf-8")
    fallback=out/"epg-fallback.xml"; build_fallback_epg(base,cfg,fallback)
    if args.real_epg: real_count,source_count=try_merge_real_epg(s,base,guides_by_channel,fallback,out/"epg.xml",args.max_epg_sources)
    else: (out/"epg.xml").write_bytes(fallback.read_bytes()); real_count,source_count=0,0
    build_epg_index(out/"epg.xml",out/"epg_index.json")
    stats={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"unique_channels":len(base),"playlist_entries":len(expanded),"groups":{g:(None if g in VIRTUAL_GROUPS else sum(1 for x in expanded if x["group"]==g)) for g in GROUP_ORDER},"channels_with_guide_metadata":sum(1 for e in base if e.get("has_guide_metadata")),"real_epg_channels_merged":real_count,"epg_sources_attempted":source_count,"epg_note":"Every included channel has an XMLTV entry. Real programme data is merged when available; otherwise the guide clearly marks schedule unavailable."}
    (out/"stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(stats,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
