#!/usr/bin/env python3
import argparse, json, re, time, gzip, html, os, hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
import xml.etree.ElementTree as ET

API = "https://iptv-org.github.io/api"
UA = "MasterTV/5.2 (+public-free-and-private-text-import)"
TIMEOUT = 25

GROUP_SECTIONS = [
    ("START", ["🏠 HOME", "⭐ FAVORITES", "🕘 RECENTLY WATCHED", "✨ FAST & FREE"]),
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
        "🏁 MOTORSPORTS OTHER", "🏌️ GOLF", "🏐 OTHER SPORTS", "🏆 SPORTS NEWS", "🎟 SPORTS EVENTS"
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
    ("💎 PREMIUM & SPORTS SERVICES", [
        "💎 PREMIUM LIVE CHANNELS", "🏀 NBA LEAGUE PASS", "⚾ MLB.TV", "🏈 NFL+", "🏎 F1 TV", "📡 ESPN"
    ]),
    ("🆓 FAST / ON DEMAND", [
        "🟢 FREE SPORTS FAST", "🎬 FREE MOVIES FAST", "📺 FREE SERIES FAST", "🎬 ON DEMAND MOVIES",
        "📺 ON DEMAND SERIES", "🆕 NEW RELEASES EN", "🆕 ESTRENOS ESPAÑOL"
    ])
]
GROUP_ORDER = [g for _, groups in GROUP_SECTIONS for g in groups]
VIRTUAL_GROUPS = {"🏠 HOME", "⭐ FAVORITES", "🕘 RECENTLY WATCHED"}
VOD_GROUPS = {"💎 PREMIUM LIVE CHANNELS","🏀 NBA LEAGUE PASS","⚾ MLB.TV","🏈 NFL+","🏎 F1 TV","📡 ESPN","🟢 FREE SPORTS FAST","🎬 FREE MOVIES FAST","📺 FREE SERIES FAST","🎬 ON DEMAND MOVIES","📺 ON DEMAND SERIES","🆕 NEW RELEASES EN","🆕 ESTRENOS ESPAÑOL"}

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
    "🏁 MOTORSPORTS OTHER": ["nascar", "indycar", "motorsport", "racing", "rally", "red bull tv"],
    "🏌️ GOLF": ["golf", "pga"],
    "🏆 SPORTS NEWS": ["sports news", "sport news", "espn news", "sportscenter"],
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
    "🏆 SPORTS EVENTS": ["sports event", "sport event", "live sports event", "match", "game", "vs."],
}

COUNTRY_HINTS = {
    "puerto rico":"PR", "colombia":"CO", "mexico":"MX", "méxico":"MX", "dominican":"DO", "republica dominicana":"DO",
    "españa":"ES", "spain":"ES", "argentina":"AR", "chile":"CL", "peru":"PE", "perú":"PE", "venezuela":"VE",
    "ecuador":"EC", "panama":"PA", "panamá":"PA", "costa rica":"CR", "guatemala":"GT", "el salvador":"SV",
    "honduras":"HN", "uruguay":"UY", "brazil":"BR", "brasil":"BR", "canada":"CA", "uk":"UK", "united kingdom":"UK",
    "france":"FR", "francia":"FR", "italy":"IT", "italia":"IT", "germany":"DE", "alemania":"DE", "usa":"US", "united states":"US"
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
    return any(x in blob for x in [" local", "local ", "regional", "municipal", "city tv", "canal local", "televisión local", "television local"])


def country_group(country, langs, cfg):
    if country=="US":
        if "spa" in langs and "eng" not in langs: return ["🇺🇸 USA | SPANISH"]
        if "spa" in langs: return ["🇺🇸 USA | ENGLISH", "🇺🇸 USA | SPANISH"]
        return ["🇺🇸 USA | ENGLISH"]
    if country in cfg["country_groups"]: return [cfg["country_groups"][country]]
    if country in cfg["latam_countries"]: return ["🌎 LATINOAMERICA"]
    return ["🌍 INTERNATIONAL"]


def enrich_groups(groups, name, raw_group, country, langs, cfg):
    rg=(raw_group or "").lower(); blob=(name+" "+(raw_group or "")).lower()
    # Map source-provided group names first.
    for c, gs in CATEGORY_MAP.items():
        if c in rg: groups.extend(gs)
    if any(x in rg for x in ["pelicula","películas","cine","movie"]): groups.append("🎬 MOVIES")
    if any(x in rg for x in ["serie","series"]): groups.append("📺 SERIES")
    if any(x in rg for x in ["infantil","kids","children"]): groups.append("👶 KIDS")
    if any(x in rg for x in ["documental","documentary"]): groups.extend(["📚 KNOWLEDGE","🌎 DOCUMENTARIES"])
    if any(x in rg for x in ["noticia","news"]): groups.append("📰 NEWS")
    if any(x in rg for x in ["musica","música","music"]): groups.append("🎵 MUSIC")
    if any(x in rg for x in ["religion","religious"]): groups.append("🙏 RELIGIOUS")
    if any(x in rg for x in ["deporte","sports","sport"]): groups.append("🏆 SPORTS")
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
    if any(x in blob for x in ["cartoon","toon","animation","anime"]): groups.append("🎨 CARTOONS / ANIMATION")
    if any(x in blob for x in ["baby", "junior", "jr.", "preschool"]): groups.append("🧸 PRESCHOOL")
    return list(dict.fromkeys(groups))


def groups_for(ch, st, cfg, langs):
    country=ch.get("country") or ""; groups=country_group(country,langs,cfg)
    if cfg.get("duplicate_into_latam") and country in cfg["latam_countries"] and "🌎 LATINOAMERICA" not in groups: groups.append("🌎 LATINOAMERICA")
    if cfg.get("duplicate_into_content_groups"):
        cats=[str(c).lower() for c in (ch.get("categories") or [])]
        for c in cats: groups.extend(CATEGORY_MAP.get(c,[]))
        groups=enrich_groups(groups, ch.get("name") or "", " ".join(cats), country, langs, cfg)
        blob=channel_blob(ch,st)
        if is_local(ch,blob):
            groups.append("📡 LOCAL TV")
            if country=="PR": groups.append("🇵🇷 PUERTO RICO LOCAL")
            elif country=="US": groups.append("🇺🇸 USA LOCAL")
            elif country=="CO": groups.append("🇨🇴 COLOMBIA LOCAL")
            elif country in cfg["latam_countries"]: groups.append("🌎 LATAM LOCAL")
        if any(g in groups for g in ["📺 SPECIAL EVENTS","🏆 SPORTS EVENTS"]): groups.append("🎟 EVENTS")
    return list(dict.fromkeys(groups))


def parse_attr_line(line):
    attrs={}
    for m in re.finditer(r'([\w-]+)="([^"]*)"', line): attrs[m.group(1).lower()]=m.group(2)
    return attrs


def infer_country(raw_group, name, default=""):
    text=(raw_group+" "+name).lower()
    for hint, code in COUNTRY_HINTS.items():
        if hint in text: return code
    return default or ""


def detect_lang(name, raw_group, attrs, country):
    raw=(attrs.get("tvg-language") or attrs.get("language") or "").lower()
    out=[]
    if any(x in raw for x in ["spanish","español","spa","es-"]): out.append("spa")
    if any(x in raw for x in ["english","eng","en-"]): out.append("eng")
    text=(name+" "+raw_group).lower()
    if not out and country in {"PR","CO","MX","DO","ES","AR","CL","PE","VE","EC","PA","CR","GT","SV","HN","UY"}: out.append("spa")
    if not out and country in {"US","UK","CA"}: out.append("eng")
    if "español" in text or "espanol" in text or "latino" in text: out.append("spa")
    return list(dict.fromkeys(out))


def stable_id(source_id, tvg_id, name, url):
    if tvg_id: return tvg_id
    h=hashlib.sha1(f"{source_id}|{name}|{url}".encode("utf-8","ignore")).hexdigest()[:16]
    return f"mtv5.{source_id}.{h}"


def source_is_blocked(url, cfg):
    low=(url or "").lower()
    return any(p.lower() in low for p in cfg.get("blocked_source_patterns",[]))


def fetch_text(session, url, cfg, allow_blocked=False):
    if source_is_blocked(url,cfg) and not allow_blocked: raise ValueError("blocked source pattern")
    r=session.get(url,timeout=int(cfg.get("external_source_timeout",35)),headers={"User-Agent":UA})
    r.raise_for_status()
    maxb=int(cfg.get("external_source_max_bytes",18_000_000))
    if len(r.content)>maxb: raise ValueError(f"playlist too large ({len(r.content)} bytes)")
    # Most M3U files are UTF-8; fallback keeps malformed accents parseable.
    try: return r.content.decode("utf-8-sig")
    except UnicodeDecodeError: return r.content.decode("latin-1","replace")


def parse_m3u(text, source, cfg):
    entries=[]; epg_urls=[]; pending=None; referrer=None; user_agent=None
    lines=text.replace("\r\n","\n").replace("\r","\n").split("\n")
    if lines and lines[0].startswith("#EXTM3U"):
        a=parse_attr_line(lines[0])
        raw=a.get("x-tvg-url") or a.get("url-tvg") or ""
        epg_urls.extend([x.strip() for x in raw.split(",") if x.strip()])
    for raw in lines:
        line=raw.strip()
        if not line: continue
        if line.startswith("#EXTINF"):
            attrs=parse_attr_line(line)
            name=line.split(",",1)[1].strip() if "," in line else attrs.get("tvg-name") or "Channel"
            pending={"attrs":attrs,"name":clean_name(name),"raw_group":attrs.get("group-title") or ""}
            referrer=None; user_agent=None
        elif line.startswith("#EXTGRP:") and pending:
            pending["raw_group"]=line.split(":",1)[1].strip()
        elif line.startswith("#EXTVLCOPT:http-referrer="):
            referrer=line.split("=",1)[1].strip()
        elif line.startswith("#EXTVLCOPT:http-user-agent="):
            user_agent=line.split("=",1)[1].strip()
        elif line.startswith("#"):
            continue
        elif pending:
            url=line
            # Nested .m3u playlist pointers are not playable channel streams.
            path=urlparse(url).path.lower()
            if path.endswith(".m3u") and not path.endswith(".m3u8"):
                pending=None; continue
            if source_is_blocked(url,cfg): pending=None; continue
            attrs=pending["attrs"]; name=pending["name"]; raw_group=pending["raw_group"]
            country=infer_country(raw_group,name,source.get("default_country") or "")
            langs=detect_lang(name,raw_group,attrs,country)
            groups=country_group(country,langs,cfg)
            if source.get("source_group"): groups.append(source["source_group"])
            groups=enrich_groups(groups,name,raw_group,country,langs,cfg)
            if cfg.get("duplicate_into_latam") and country in cfg["latam_countries"] and "🌎 LATINOAMERICA" not in groups: groups.append("🌎 LATINOAMERICA")
            tvg_id=stable_id(source["id"],attrs.get("tvg-id") or "",name,url)
            entries.append({
                "tvg_id":tvg_id,"name":name,"url":url,"logo":attrs.get("tvg-logo") or "","groups":list(dict.fromkeys(groups)),
                "country":country,"languages":langs,"quality":"","labels":["FAST/Public"] if source.get("public_free") else ["Authorized"],
                "referrer":referrer,"user_agent":user_agent,"has_guide_metadata":bool(attrs.get("tvg-id")),
                "source":source.get("name") or source["id"],"source_id":source["id"],"source_priority":int(source.get("priority",50)),
                "source_kind":"public-free" if source.get("public_free") else "authorized"
            })
            pending=None
    return entries, epg_urls


def normalize_name(s):
    s=(s or "").lower()
    s=re.sub(r"\b(?:hd|fhd|uhd|4k|sd|1080p|720p|channel|canal|tv)\b"," ",s)
    s=re.sub(r"[^a-z0-9áéíóúñ]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()


def score_entry(e):
    score=int(e.get("source_priority",50))*100
    if e.get("url","").startswith("https://"): score+=30
    score+=quality_rank(e.get("quality"))
    if e.get("logo"): score+=5
    if e.get("has_guide_metadata"): score+=10
    return score


def dedupe_entries(entries):
    by_url={}; by_key={}
    for e in entries:
        if not e.get("url"): continue
        if e["url"] in by_url:
            old=by_url[e["url"]]; old["groups"]=list(dict.fromkeys((old.get("groups") or [])+(e.get("groups") or [])))
            continue
        by_url[e["url"]]=e
    for e in by_url.values():
        key=(normalize_name(e.get("name")), e.get("country") or "")
        if not key[0]: key=(e.get("tvg_id"),e.get("country") or "")
        old=by_key.get(key)
        if not old or score_entry(e)>score_entry(old):
            if old:
                e["groups"]=list(dict.fromkeys((old.get("groups") or [])+(e.get("groups") or [])))
            by_key[key]=e
        else:
            old["groups"]=list(dict.fromkeys((old.get("groups") or [])+(e.get("groups") or [])))
    return list(by_key.values())


def xmltv_dt(dt): return dt.strftime("%Y%m%d%H%M%S +0000")


def build_fallback_epg(entries,cfg,out_path):
    root=ET.Element("tv",{"generator-info-name":"MasterTV V5 Fusion"}); seen=set()
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


def merge_xmltv_url(session, base, u, wanted, channel_seen, real):
    try:
        r=session.get(u,timeout=18,headers={"User-Agent":UA})
        if r.status_code!=200 or len(r.content)>60_000_000: return False
        data=r.content
        if u.endswith(".gz") or data[:2]==b"\x1f\x8b": data=gzip.decompress(data)
        root=ET.fromstring(data)
        for ce in root.findall("channel"):
            cid=ce.attrib.get("id")
            if cid in wanted and cid not in channel_seen: base.append(ce); channel_seen.add(cid)
        for pe in root.findall("programme"):
            cid=pe.attrib.get("channel")
            if cid in wanted: base.append(pe); real.add(cid)
        return True
    except Exception:
        return False


def try_merge_real_epg(session,entries,guides_by_channel,fallback_path,out_path,max_sources=120,extra_sources=None):
    wanted={e["tvg_id"] for e in entries}; sources=[]
    for cid in wanted:
        for g in guides_by_channel.get(cid,[]):
            for s in g.get("sources") or []:
                u=s.get("url")
                if u and u not in sources: sources.append(u)
    for u in (extra_sources or []):
        if u and u not in sources: sources.append(u)
    sources=sources[:max_sources]
    base=ET.parse(fallback_path).getroot(); channel_seen={x.attrib.get("id") for x in base.findall("channel")}; real=set(); attempted=0
    for u in sources:
        attempted+=1; merge_xmltv_url(session,base,u,wanted,channel_seen,real)
    for pe in list(base.findall("programme")):
        cid=pe.attrib.get("channel"); title=pe.findtext("title") or ""
        if cid in real and title.startswith("Live programming"): base.remove(pe)
    ET.ElementTree(base).write(out_path,encoding="utf-8",xml_declaration=True)
    return len(real),attempted


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
        def pack(x): return None if not x else {"start":x[0].isoformat(),"stop":x[1].isoformat(),"title":x[2],"desc":x[3]}
        idx[cid]={"now":pack(current),"next":pack(nxt)}
    out_path.write_text(json.dumps(idx,ensure_ascii=False,separators=(",",":")),encoding="utf-8")


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="config.json"); ap.add_argument("--out",default="output"); ap.add_argument("--real-epg",action="store_true"); ap.add_argument("--max-epg-sources",type=int,default=160); args=ap.parse_args()
    root=Path(__file__).resolve().parent; cfg=json.loads((root/args.config).read_text(encoding="utf-8")); out=root/args.out; out.mkdir(parents=True,exist_ok=True); cache=root/".cache"
    s=requests.Session(); s.headers.update({"User-Agent":UA})
    source_stats=[]; extra_epg=[]; all_entries=[]

    # 1) IPTV-org API base.
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
    intl_count=0; base=[]
    for st in best:
        cid=st["channel"]; ch=ch_by_id[cid]; langs=langs_for(cid,st.get("feed"),feeds_by_key,guides_by_channel); groups=groups_for(ch,st,cfg,langs)
        if groups==["🌍 INTERNATIONAL"]:
            if intl_count>=int(cfg.get("international_limit",4500)): continue
            intl_count+=1
        base.append({"tvg_id":cid,"name":clean_name(st.get("title") or ch.get("name") or cid),"url":st["url"],"logo":pick_logo(logos_by_channel.get(cid,[])),"groups":groups,"country":ch.get("country") or "","languages":langs,"quality":st.get("quality") or "","labels":st.get("labels") or [],"referrer":st.get("referrer"),"user_agent":st.get("user_agent"),"has_guide_metadata":bool(guides_by_channel.get(cid)),"source":"IPTV-org","source_id":"iptv-org","source_priority":85,"source_kind":"public-index"})
    all_entries.extend(base); source_stats.append({"id":"iptv-org","name":"IPTV-org","status":"ok","entries":len(base)})

    # 2) Curated public/free M3U sources.
    sources=list(cfg.get("external_sources") or [])
    # Optional private/authorized M3Us can be supplied as a GitHub secret, one URL per line. We never ship credentials in the repo.
    auth_urls=[x.strip() for x in os.getenv("MASTERTV_AUTHORIZED_M3U_URLS","").splitlines() if x.strip()]
    for i,u in enumerate(auth_urls,1):
        sources.append({"id":f"authorized-{i}","name":f"Authorized source {i}","url":u,"priority":95,"public_free":False})

    # Optional private FORTV imports. Keep credentials/URLs out of the public repo.
    # 1) A normal playlist URL can still be supplied when the user has one.
    fortv_url=os.getenv("FORTV_M3U_URL","").strip()
    if fortv_url:
        sources.append({"id":"fortv-private-url","name":"FORTV (private authorized)","url":fortv_url,"priority":98,"public_free":False,"source_group":"💎 PREMIUM LIVE CHANNELS","allow_blocked":True})

    # 2) Easy Import: paste an entire M3U block into one GitHub Actions secret.
    #    For long playlists, additional numbered chunks are concatenated automatically.
    fortv_parts=[]
    for key in ["FORTV_M3U_TEXT"]+[f"FORTV_M3U_TEXT_{i}" for i in range(2,9)]:
        val=os.getenv(key,"")
        if val.strip(): fortv_parts.append(val)
    fortv_text="\n".join(fortv_parts).strip()
    if fortv_text:
        src={"id":"fortv-private-text","name":"FORTV Easy Import (private authorized)","priority":99,"public_free":False,"source_group":"💎 PREMIUM LIVE CHANNELS"}
        ents,epgs=parse_m3u(fortv_text,src,{**cfg,"blocked_source_patterns":[]})
        # This secret is specifically for FORTV. Ignore unrelated pasted entries.
        ents=[e for e in ents if "fortv.cc" in (e.get("url") or "").lower()]
        all_entries.extend(ents); extra_epg.extend(epgs)
        source_stats.append({"id":src["id"],"name":src["name"],"status":"ok","entries":len(ents),"epg_urls":len(epgs),"import_mode":"secret-text"})

    for src in sources:
        try:
            text=fetch_text(s,src["url"],cfg,allow_blocked=bool(src.get("allow_blocked"))); ents,epgs=parse_m3u(text,src,{**cfg,"blocked_source_patterns":[]} if src.get("allow_blocked") else cfg); all_entries.extend(ents); extra_epg.extend(epgs)
            source_stats.append({"id":src["id"],"name":src.get("name",src["id"]),"status":"ok","entries":len(ents),"epg_urls":len(epgs)})
        except Exception as e:
            source_stats.append({"id":src.get("id","source"),"name":src.get("name",src.get("id","source")),"status":"error","entries":0,"error":str(e)[:180]})

    merged=dedupe_entries(all_entries)
    order={g:i for i,g in enumerate(GROUP_ORDER)}; expanded=[]
    for e in merged:
        for g in e.get("groups") or []:
            if g in VIRTUAL_GROUPS or g in VOD_GROUPS: continue
            x=dict(e); x["group"]=g; expanded.append(x)
    expanded.sort(key=lambda e:(order.get(e["group"],999),e["name"].lower(),e["tvg_id"]))

    with (out/"master.m3u").open("w",encoding="utf-8") as f:
        f.write('#EXTM3U x-tvg-url="epg.xml"\n')
        for e in expanded:
            attrs=[f'tvg-id="{html.escape(e["tvg_id"],quote=True)}"',f'tvg-name="{html.escape(e["name"],quote=True)}"',f'group-title="{html.escape(e["group"],quote=True)}"']
            if e.get("logo"): attrs.append(f'tvg-logo="{html.escape(e["logo"],quote=True)}"')
            f.write('#EXTINF:-1 '+' '.join(attrs)+','+e['name']+'\n')
            if e.get("referrer"): f.write(f'#EXTVLCOPT:http-referrer={e["referrer"]}\n')
            if e.get("user_agent"): f.write(f'#EXTVLCOPT:http-user-agent={e["user_agent"]}\n')
            f.write(e['url']+'\n')

    (out/"channels.json").write_text(json.dumps(merged,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (out/"groups.json").write_text(json.dumps(GROUP_ORDER,ensure_ascii=False),encoding="utf-8")
    (out/"group_sections.json").write_text(json.dumps([{"title":t,"groups":g} for t,g in GROUP_SECTIONS],ensure_ascii=False),encoding="utf-8")
    (out/"sources.json").write_text(json.dumps(source_stats,ensure_ascii=False,indent=2),encoding="utf-8")

    fallback=out/"epg-fallback.xml"; build_fallback_epg(merged,cfg,fallback)
    if args.real_epg: real_count,source_count=try_merge_real_epg(s,merged,guides_by_channel,fallback,out/"epg.xml",args.max_epg_sources,extra_epg)
    else: (out/"epg.xml").write_bytes(fallback.read_bytes()); real_count,source_count=0,0
    build_epg_index(out/"epg.xml",out/"epg_index.json")

    stats={"version":"V5.2","generated_at_utc":datetime.now(timezone.utc).isoformat(),"unique_channels":len(merged),"playlist_entries":len(expanded),"groups":{g:(None if g in VIRTUAL_GROUPS or g in VOD_GROUPS else sum(1 for x in expanded if x["group"]==g)) for g in GROUP_ORDER},"channels_with_guide_metadata":sum(1 for e in merged if e.get("has_guide_metadata")),"real_epg_channels_merged":real_count,"epg_sources_attempted":source_count,"sources":source_stats,"epg_note":"Every included channel has an XMLTV entry. Real programme data is merged when available; otherwise the guide clearly marks schedule unavailable."}
    (out/"stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"unique_channels":len(merged),"playlist_entries":len(expanded),"sources":source_stats,"real_epg_channels":real_count},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
