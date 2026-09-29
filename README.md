# MasterTV V2 Full Expanded

MasterTV V2 builds a self-updating public/free-stream M3U library, XMLTV EPG, and responsive PWA for phones, tablets and Tesla Chromium. It preserves `tvg-id`, logos, languages, country metadata and stream quality, while exposing a much larger fixed navigation structure.

## Library

- ⭐ FAVORITES — saved locally on each device
- 🕘 RECENTLY WATCHED — automatically updated on playback, up to 50 channels

## Countries / Regions

Puerto Rico, USA English, USA Spanish, Colombia, Mexico, Dominican Republic, Spain, Argentina, Chile, Peru, Venezuela, Ecuador, Panama, Costa Rica, Guatemala, El Salvador, Honduras, Uruguay, Brazil, Latinoamerica, UK, Canada, France, Italy, Germany and International.

## Sports

Sports, NFL/Football, MLB/Baseball, NBA/Basketball, NHL/Hockey, Soccer/Fútbol, Tennis, Boxing, MMA/Combat Sports, F1/Motorsports, Motorsports Other, Golf, Other Sports and Sports News.

## Entertainment / Kids / News / Knowledge / Music / Religious

Includes Movies, Classic Movies, Comedy, Drama, Action, Horror, Romance, Western, Sci-Fi, Series, General Entertainment, Kids, Cartoons/Animation, Preschool, Family, News subgroups, Weather, Documentaries, Science, Nature, History, Travel, Cooking, Automotive, Latin Music, Rock/Pop, Music Videos, Radio, Christian, Catholic and Other Religious.

## Local TV and Events

Includes:

- 📡 LOCAL TV
- 🇵🇷 PUERTO RICO LOCAL
- 🇺🇸 USA LOCAL
- 🇨🇴 COLOMBIA LOCAL
- 🌎 LATAM LOCAL
- 🎟 EVENTS
- 📺 SPECIAL EVENTS
- 🏆 SPORTS EVENTS

Event categories are populated only when public stream metadata/title information identifies an event source. MasterTV does not add unauthorized PPV or stolen premium feeds.

## EPG

Every included channel receives a valid XMLTV entry. Where reliable programme-level data is available from guide metadata, `--real-epg` merges it. Where it is not available, MasterTV creates a clearly labeled fallback (`Live programming — schedule unavailable`) rather than fabricating programme names.

The web player also generates `epg_index.json` for fast NOW/NEXT display without forcing phones or Tesla browsers to parse a large XML file.

## Build locally

```bash
python3 -m pip install -r requirements.txt
python3 update_master.py --real-epg --max-epg-sources 120
python3 -m http.server 8080
```

Open `http://localhost:8080/static/`.

Generated outputs:

- `output/master.m3u`
- `output/epg.xml`
- `output/channels.json`
- `output/groups.json`
- `output/group_sections.json`
- `output/epg_index.json`
- `output/stats.json`

## Automatic updates

The included GitHub Actions workflow runs daily, rebuilds the M3U and EPG, commits refreshed output, and deploys the PWA to GitHub Pages.

## Tesla Model 3

The UI uses large touch targets and responsive layouts. Front-screen video remains subject to Tesla's own Park restriction. MasterTV does not attempt to bypass vehicle safety restrictions. Rear-screen playback behavior remains controlled by Tesla software and vehicle configuration.

## Legal/use note

Designed for public/free streams and sources the user is authorized to access. It does not include stolen Xtream credentials or pirate PPV feeds.
