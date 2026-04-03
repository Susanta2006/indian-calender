import warnings
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import calendar

import geocoder
import numpy as np
import pyfiglet
from skyfield.almanac import find_discrete, moon_phases, risings_and_settings
from skyfield.api import load, wgs84

# Suppress skyfield/numpy warnings
warnings.filterwarnings("ignore")

############################# BANNER #############################
banner_text = pyfiglet.figlet_format("Ind-Panchang")
print(banner_text)
print(" version 5.4 (Precision: Paksha & Tithi Alignment)")
print(" Created by Mr. Susanta Banik | Precision-Refined\n")

# ---------------- CONFIG & LOCATION ----------------

try:
    g = geocoder.ip("me")
    if g.ok and g.latlng:
        LAT, LON = g.latlng
        CITY, STATE = g.city or "Unknown City", g.state or "Unknown State"
    else:
        LAT, LON = 23.8315, 91.2868
        CITY, STATE = "Agartala", "Tripura"
except Exception:
    LAT, LON = 23.8315, 91.2868
    CITY, STATE = "Agartala", "Tripura"

ZONE = "Asia/Kolkata"
ts = load.timescale()
eph = load("de421.bsp")
earth, sun, moon = eph["earth"], eph["sun"], eph["moon"]
location = wgs84.latlon(LAT, LON)

# ---------------- DATA TABLES ----------------

lunar_months = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada", "Ashwin", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna"]

tithi_names = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", 
    "Shashti", "Saptami", "Ashtami", "Navami", "Dashami", 
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"
]

# ---------------- CORE HELPERS ----------------

def get_tithi_name(num, paksha):
    if num == 15:
        return "Purnima" if paksha == "Shukla" else "Amavasya"
    return tithi_names[num-1]

def to_ist(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo(ZONE))

def get_lon(body, t):
    return earth.at(t).observe(body).apparent().ecliptic_latlon()[1].degrees % 360   #type: ignore

def get_tithi_at(t):
    s_lon = get_lon(sun, t)
    m_lon = get_lon(moon, t)
    return ((m_lon - s_lon) % 360) / 12

# ---------------- CALCULATION FUNCTIONS ----------------

def get_sun_moon_times(dt_local):
    t0 = ts.from_datetime(dt_local.replace(hour=0, minute=0, second=0, microsecond=0))
    t1 = ts.from_datetime(dt_local.replace(hour=23, minute=59, second=59))
    res = {}
    for body, name in [(sun, "sun"), (moon, "moon")]:
        f = risings_and_settings(eph, body, location)
        times, events = find_discrete(t0, t1, f)
        res[f"{name}rise"] = None
        res[f"{name}set"] = None
        for t, e in zip(times, events):
            if e == 1: res[f"{name}rise"] = to_ist(t.utc_datetime())
            else: res[f"{name}set"] = to_ist(t.utc_datetime())
    return res

def get_moon_phases_detailed(dt_now):
    t0 = ts.from_datetime(dt_now - timedelta(days=10))
    t1 = ts.from_datetime(dt_now + timedelta(days=10))
    f = moon_phases(eph)
    times, values = find_discrete(t0, t1, f)
    ph_names = ["New Moon", "First Quarter", "Full Moon", "Last Quarter"]
    for i in range(len(times)-1):
        if times[i].utc_datetime() <= dt_now.astimezone(ZoneInfo("UTC")) <= times[i+1].utc_datetime():
            return {
                "name": ph_names[values[i]],
                "start": to_ist(times[i].utc_datetime()).strftime('%d %b %Y, %I:%M:%S %p'),
                "end": to_ist(times[i+1].utc_datetime()).strftime('%d %b %Y, %I:%M:%S %p'),
                "next_name": ph_names[values[i+1]]
            }
    return None

def get_eclipse_data(dt_now):
    from skyfield import eclipselib
    t0 = ts.from_datetime(dt_now - timedelta(days=180))
    t1 = ts.from_datetime(dt_now + timedelta(days=180))
    eclipses = []
    
    try:
        l_times, _, _ = eclipselib.lunar_eclipses(t0, t1, eph)
        for t in l_times:
            eclipses.append(f"LUNAR ECLIPSE: {to_ist(t.utc_datetime()).strftime('%d %b %Y, %I:%M %p')}")
    except Exception: pass

    try:
        if hasattr(eclipselib, 'solar_eclipses'):
            s_times, _, _ = eclipselib.solar_eclipses(t0, t1, eph) #type: ignore
            for t in s_times:
                eclipses.append(f"SOLAR ECLIPSE: {to_ist(t.utc_datetime()).strftime('%d %b %Y, %I:%M %p')}")
        else:
            from skyfield import almanac
            t_nm, _ = almanac.find_discrete(t0, t1, almanac.moon_phases(eph))
            for t in t_nm:
                e = earth.at(t) #type: ignore
                s = e.observe(sun).apparent()
                m = e.observe(moon).apparent()
                _, _, distance = s.separation_from(m)
                if distance.degrees < 1.6:
                    eclipses.append(f"SOLAR ECLIPSE (Potential): {to_ist(t.utc_datetime()).strftime('%d %b %Y, %I:%M %p')}")
    except Exception: pass
        
    return sorted(list(set(eclipses)))

def get_easter_related(year):
    # Meeus/Jones/Butcher algorithm
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mo = (h + l - 7 * m + 114) // 31
    da = ((h + l - 7 * m + 114) % 31) + 1
    easter = datetime(year, mo, da, tzinfo=ZoneInfo(ZONE))
    return {
        "Easter Sunday": easter,
        "Good Friday": easter - timedelta(days=2),
        "Palm Sunday": easter - timedelta(days=7),
        "Ash Wednesday": easter - timedelta(days=46)
    }

def get_lunar_month_name(dt_local):
    t = ts.from_datetime(dt_local)
    ayan = 24.25
    sun_sidereal = (get_lon(sun, t) - ayan) % 360
    return lunar_months[int(sun_sidereal // 30)]

def get_monthly_transitions(dt_now):
    year, month = dt_now.year, dt_now.month
    _, last_day = calendar.monthrange(year, month)
    # Scan a wide range to catch transitions starting before or ending after current month
    t_start = ts.from_datetime(datetime(year, month, 1, tzinfo=ZoneInfo(ZONE)) - timedelta(days=2))
    t_end = ts.from_datetime(datetime(year, month, last_day, 23, 59, 59, tzinfo=ZoneInfo(ZONE)) + timedelta(days=5))
    
    def tithi_crossing(t): return np.floor(get_tithi_at(t))
    tithi_crossing.step_days = 0.1   #type: ignore
    times, values = find_discrete(t_start, t_end, tithi_crossing)
    
    transitions = []
    for i in range(len(times)):
        t_ist = to_ist(times[i].utc_datetime())
        # Tithi value is 0-29.99
        # 0-14.99 is Shukla Paksha (Waxing)
        # 15-29.99 is Krishna Paksha (Waning)
        raw_val = int(values[i]) % 30
        if raw_val < 15:
            paksha = "Shukla"
            num = raw_val + 1
        else:
            paksha = "Krishna"
            num = raw_val - 14
        transitions.append({"num": num, "paksha": paksha, "time": t_ist, "raw": raw_val})
    return transitions

# ---------------- FESTIVAL DATABASE ----------------

TITHI_DB = [
    ("Magha", "Shukla", 4, "Ganesh Jayanti"),
    ("Magha", "Shukla", 5, "Vasant Panchami / Saraswati Puja"),
    ("Magha", "Shukla", 7, "Ratha Saptami"),
    ("Magha", "Shukla", 11, "Jaya Ekadashi"),
    ("Magha", "Shukla", 15, "Magha Purnima / Guru Ravidas Jayanti"),
    ("Phalguna", "Krishna", 11, "Vijaya Ekadashi"),
    ("Phalguna", "Krishna", 14, "Maha Shivaratri"),
    ("Phalguna", "Shukla", 11, "Amalaki Ekadashi"),
    ("Phalguna", "Shukla", 15, "Holi / Dol Jatra"),
    ("Chaitra", "Shukla", 1, "Ugadi / Gudi Padwa / Chaitra Navratri"),
    ("Chaitra", "Shukla", 2, "Jhulelal Jayanti"),
    ("Chaitra", "Shukla", 3, "Gangaur / Gauri Puja"),
    ("Chaitra", "Shukla", 9, "Rama Navami"),
    ("Chaitra", "Shukla", 11, "Kamada Ekadashi"),
    ("Chaitra", "Shukla", 13, "Mahavir Jayanti (Jain)"),
    ("Chaitra", "Shukla", 15, "Hanuman Janmotsav"),
    ("Vaishakha", "Krishna", 11, "Varuthini Ekadashi"),
    ("Vaishakha", "Shukla", 3, "Akshaya Tritiya / Parashurama Jayanti"),
    ("Vaishakha", "Shukla", 11, "Mohini Ekadashi"),
    ("Vaishakha", "Shukla", 15, "Buddha Purnima"),
    ("Jyeshtha", "Shukla", 11, "Nirjala Ekadashi"),
    ("Jyeshtha", "Shukla", 15, "Vat Purnima"),
    ("Ashadha", "Shukla", 2, "Jagannath Rath Yatra"),
    ("Ashadha", "Shukla", 11, "Devshayani Ekadashi"),
    ("Ashadha", "Shukla", 15, "Guru Purnima / Vyasa Puja"),
    ("Shravana", "Shukla", 3, "Hariyali Teej"),
    ("Shravana", "Shukla", 5, "Nag Panchami"),
    ("Shravana", "Shukla", 11, "Shravana Putrada Ekadashi"),
    ("Shravana", "Shukla", 15, "Raksha Bandhan / Narali Purnima"),
    ("Bhadrapada", "Krishna", 3, "Kajari Teej"),
    ("Bhadrapada", "Krishna", 8, "Krishna Janmashtami"),
    ("Bhadrapada", "Shukla", 4, "Ganesh Chaturthi"),
    ("Bhadrapada", "Shukla", 5, "Rishi Panchami"),
    ("Bhadrapada", "Shukla", 11, "Parsva Ekadashi"),
    ("Bhadrapada", "Shukla", 14, "Anant Chaturdashi"),
    ("Bhadrapada", "Shukla", 15, "Bhadrapada Purnima"),
    ("Ashwin", "Krishna", 15, "Mahalaya / Sarva Pitru Amavasya"),
    ("Ashwin", "Shukla", 1, "Shardiya Navratri Begins"),
    ("Ashwin", "Shukla", 8, "Durga Ashtami / Maha Ashtami"),
    ("Ashwin", "Shukla", 9, "Maha Navami"),
    ("Ashwin", "Shukla", 10, "Vijaya Dashami / Dussehra"),
    ("Ashwin", "Shukla", 11, "Papankusha Ekadashi"),
    ("Ashwin", "Shukla", 15, "Sharad Purnima / Kojagari Lakshmi Puja"),
    ("Kartika", "Krishna", 4, "Karwa Chauth"),
    ("Kartika", "Krishna", 13, "Dhanteras"),
    ("Kartika", "Krishna", 14, "Narak Chaturdashi"),
    ("Kartika", "Krishna", 15, "Diwali / Lakshmi Puja"),
    ("Kartika", "Shukla", 1, "Govardhan Puja / Annakut"),
    ("Kartika", "Shukla", 2, "Bhai Dooj"),
    ("Kartika", "Shukla", 6, "Chhath Puja"),
    ("Kartika", "Shukla", 11, "Devutthana Ekadashi / Tulsi Vivah"),
    ("Kartika", "Shukla", 15, "Kartik Purnima / Guru Nanak Jayanti"),
    ("Margashirsha", "Shukla", 11, "Gita Jayanti / Mokshada Ekadashi"),
    ("Margashirsha", "Shukla", 15, "Margashirsha Purnima / Dattatreya Jayanti"),
    ("Pausha", "Shukla", 11, "Pausha Putrada Ekadashi"),
    ("Pausha", "Shukla", 15, "Pausha Purnima"),
]

FIXED_DB = [
    (1, 1, "New Year"), (1, 12, "National Youth Day (Swami Vivekananda)"),
    (1, 14, "Makar Sankranti / Pongal / Magh Bihu"), (1, 15, "Indian Army Day"),
    (1, 23, "Netaji Jayanti"), (1, 26, "Republic Day"), (2, 28, "National Science Day"),
    (4, 13, "Vaisakhi / Baisakhi"), (4, 14, "Ambedkar Jayanti / Pohela Boishakh / Vishu"),
    (5, 1, "International Labour Day"), (6, 21, "International Yoga Day"),
    (8, 15, "Independence Day"), (9, 5, "Teachers' Day"), (10, 2, "Gandhi Jayanti"),
    (10, 31, "Rashtriya Ekta Diwas"), (11, 14, "Children's Day"), (12, 25, "Christmas")
]

# ---------------- RUNNER ----------------

def run_panchang():
    now_ist = datetime.now(ZoneInfo(ZONE))
    moon_info = get_moon_phases_detailed(now_ist)
    transitions = get_monthly_transitions(now_ist)
    sm = get_sun_moon_times(now_ist)
    eclipses = get_eclipse_data(now_ist)
    
    current_idx = -1
    for i in range(len(transitions)-1):
        if transitions[i]['time'] <= now_ist <= transitions[i+1]['time']:
            current_idx = i
            break
    
    fests = []
    y, m = now_ist.year, now_ist.month
    
    # Static Dates
    for fm, fd, fn in FIXED_DB:
        if fm == m: fests.append(f"{fd:02d} {now_ist.strftime('%b')}: {fn} (Solar/Fixed)")
    
    # Christian Feasts
    c_feasts = get_easter_related(y)
    for name, dt in c_feasts.items():
        if dt.month == m: fests.append(f"{dt.strftime('%d %b')}: {name} (Liturgical)")

    # Hindu Festivals based on Tithi
    for i in range(len(transitions)-1):
        tr = transitions[i]
        l_month = get_lunar_month_name(tr['time'])
        if tr['time'].month == m:
            for tm, tp, tn, name in TITHI_DB:
                if l_month == tm and tr['num'] == tn and tr['paksha'] == tp:
                    st, et = tr['time'], transitions[i+1]['time']
                    fests.append(f"{st.strftime('%d %b')}: {name} [Starts: {st.strftime('%I:%M:%S %p')} | Ends: {et.strftime('%I:%M:%S %p')}]")

    # Islamic (Lunar Window)
    for tr in transitions:
        if tr['paksha'] == "Krishna" and tr['num'] == 15 and tr['time'].month == m: # Amavasya
            eid_t = tr['time'] + timedelta(days=1)
            fests.append(f"{eid_t.strftime('%d %b')}: Eid-ul-Fitr (Approx Lunar Window)")

    fests = sorted(list(set(fests)))

    print(f"📍 LOCATION: {CITY}, {STATE}")
    print(f"📅 {now_ist.strftime('%A, %d %b %Y')} | ⏰ {now_ist.strftime('%I:%M:%S %p IST')}")
    print("="*105)
    
    if current_idx != -1:
        curr = transitions[current_idx]
        nxt = transitions[current_idx+1]
        nnxt = transitions[current_idx+2] if current_idx+2 < len(transitions) else None
        
        curr_t_name = get_tithi_name(curr['num'], curr['paksha'])
        nxt_t_name = get_tithi_name(nxt['num'], nxt['paksha'])
        
        print(f"CURRENT TITHI: {curr_t_name} ({curr['paksha']} Paksha)")
        print(f"   • Started: {curr['time'].strftime('%d %b, %I:%M:%S %p')}")
        print(f"   • Ending:  {nxt['time'].strftime('%d %b, %I:%M:%S %p')} (EXACT)")
        print(f"NEXT TITHI:    {nxt_t_name} ({nxt['paksha']} Paksha)")
        print(f"   • Starts:  {nxt['time'].strftime('%d %b, %I:%M:%S %p')}")
        if nnxt: 
            nnxt_t_name = get_tithi_name(nnxt['num'], nnxt['paksha'])
            print(f"   • Ends:    {nnxt['time'].strftime('%d %b, %I:%M:%S %p')} (Approx)")
    
    print("-" * 105)
    print(f"SUNRISE: {sm['sunrise'].strftime('%I:%M:%S %p') if sm['sunrise'] else 'N/A':20} | SUNSET: {sm['sunset'].strftime('%I:%M:%S %p') if sm['sunset'] else 'N/A'}")
    print(f"MOONRISE: {sm['moonrise'].strftime('%I:%M:%S %p') if sm['moonrise'] else 'N/A':19} | MOONSET: {sm['moonset'].strftime('%I:%M:%S %p') if sm['moonset'] else 'N/A'}")
    print("-" * 105)
    
    if moon_info:
        print(f"🌙 CURRENT MOON PHASE: {moon_info['name']}")
        print(f"   • Phase Started: {moon_info['start']}")
        print(f"   • Phase Ends:    {moon_info['end']} (Next: {moon_info['next_name']})")
    
    if eclipses:
        print("-" * 105)
        print("🌘 UPCOMING ECLIPSES (GLOBAL SCAN):")
        for e in eclipses: print(f"  • {e}")
    print("-" * 105)

    print(f"🗓️  100% COMPREHENSIVE FESTIVAL CALENDAR ({now_ist.strftime('%B %Y')}):")
    for f in fests: print(f"  • {f}")
    
    print("-" * 105)
    print("🔭 UPCOMING TITHI TRANSITIONS (NEXT 48H):")
    for tr in transitions:
        if now_ist < tr['time'] < now_ist + timedelta(hours=48):
            idx = transitions.index(tr)
            et = transitions[idx+1]['time'].strftime('%I:%M:%S %p') if idx+1 < len(transitions) else "N/A"
            tr_t_name = get_tithi_name(tr['num'], tr['paksha'])
            print(f"  ➜ {tr['time'].strftime('%d %b, %I:%M:%S %p')}: {tr_t_name} ({tr['paksha']} Paksha) Begins [Ends: {et}]")
    print("="*105)

if __name__ == "__main__":
    run_panchang()