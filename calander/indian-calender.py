# corrected_ind_calender.py
from datetime import datetime, timedelta
from skyfield.api import load, wgs84
from skyfield.almanac import risings_and_settings, find_discrete, moon_phases
from hijridate import Gregorian
from zoneinfo import ZoneInfo
import pyfiglet
import warnings
import geocoder
from timezonefinder import TimezoneFinder

############################# BANNER #######
banner_text = pyfiglet.figlet_format("Ind-Calendar")
print(banner_text, "\n version 1.1")
print()
warnings.filterwarnings("ignore")
############################################

print(
    """
**********************************
* ------------------------------ *
* |Created by Mr. Susanta Banik| *
* ------------------------------ *
**********************************
"""
)

# ---------------- CONFIG ----------------
# ---------------- CONFIG ----------------
try:
    g = geocoder.ip("me")   # detect location by IP
    if g.ok and g.latlng:
        latitude, longitude = g.latlng
        city = g.city if g.city else "Unknown City"
        state = g.state if g.state else "Unknown State"

        # Detect timezone from coordinates
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=longitude, lat=latitude)
        if not timezone_str:
            timezone_str = "Asia/Kolkata"  # fallback

    else:
        # fallback (Agartala if detection fails)
        latitude, longitude = 23.8315, 91.2868
        city, state = "Agartala", "Tripura"
        timezone_str = "Asia/Kolkata"
except Exception:
    latitude, longitude = 23.8315, 91.2868
    city, state = "Agartala", "Tripura"
    timezone_str = "Asia/Kolkata"
    
ts = load.timescale()
eph = load("de421.bsp")
earth, sun, moon = eph["earth"], eph["sun"], eph["moon"]
location = wgs84.latlon(latitude, longitude)

bengali_months = [
    "Boishakh","Jyoishtho","Asharh","Shraban","Bhadro","Ashwin",
    "Kartik","Ogrohayon","Poush","Magh","Falgun","Chaitra"
]

nakshatras = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha",
    "Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha",
    "Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

yogas = [
    "Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarman","Dhriti","Shula",
    "Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi","Vyatipata","Variyana",
    "Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"
]

karanas = ["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti"]

# ---------------- HELPERS ----------------
def to_ist(dt): 
    return dt.astimezone(ZoneInfo(timezone_str))
def to_utc(dt): 
    return dt.astimezone(ZoneInfo("UTC"))
def normalize_angle(angle): 
    return angle % 360
    
def get_utc_times_for_local_day(dt_local):
    local_zone = ZoneInfo(timezone_str)
    local_midnight = datetime(dt_local.year, dt_local.month, dt_local.day, 0, 0, tzinfo=local_zone)
    local_end = datetime(dt_local.year, dt_local.month, dt_local.day, 23, 59, 59, tzinfo=local_zone)
    return local_midnight.astimezone(ZoneInfo("UTC")), local_end.astimezone(ZoneInfo("UTC"))

def get_sunrise_sunset(dt_local):
    f = risings_and_settings(eph, sun, location)
    t0_utc, t1_utc = get_utc_times_for_local_day(dt_local)
    t0, t1 = ts.from_datetime(t0_utc), ts.from_datetime(t1_utc)
    times, events = find_discrete(t0, t1, f)
    sunrise = sunset = None
    for t, e in zip(times, events):
        dt_ist = to_ist(t.utc_datetime().replace(tzinfo=ZoneInfo("UTC")))
        if e in (True, 1): sunrise = dt_ist
        else: sunset = dt_ist
    return sunrise, sunset

def get_moonrise_moonset(dt_local):
    f = risings_and_settings(eph, moon, location)
    t0_utc, t1_utc = get_utc_times_for_local_day(dt_local)
    t0, t1 = ts.from_datetime(t0_utc), ts.from_datetime(t1_utc)
    times, events = find_discrete(t0, t1, f)
    moonrise = moonset = None
    for t, e in zip(times, events):
        dt_ist = to_ist(t.utc_datetime().replace(tzinfo=ZoneInfo("UTC")))
        if e in (True, 1): moonrise = dt_ist
        else: moonset = dt_ist
    return moonrise, moonset

def sun_longitude(dt_local):
    t = ts.from_datetime(to_utc(dt_local))
    return normalize_angle(earth.at(t).observe(sun).apparent().ecliptic_latlon()[1].degrees)

def moon_longitude(dt_local):
    t = ts.from_datetime(to_utc(dt_local))
    return normalize_angle(earth.at(t).observe(moon).apparent().ecliptic_latlon()[1].degrees)

def compute_tithi(sun_lon, moon_lon):
    angle = normalize_angle(moon_lon - sun_lon)
    tithi_num = int(angle // 12) + 1
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    if tithi_num > 15: tithi_num -= 15
    return tithi_num, paksha

def compute_nakshatra(moon_lon):
    AYANAMSHA = 24.25
    sidereal_moon_lon = normalize_angle(moon_lon - AYANAMSHA)
    return nakshatras[int(sidereal_moon_lon / (360 / 27))]

def compute_yoga(sun_lon, moon_lon):
    AYANAMSHA = 24.25
    sidereal_sun_lon = normalize_angle(sun_lon - AYANAMSHA)
    sidereal_moon_lon = normalize_angle(moon_lon - AYANAMSHA)
    total = normalize_angle(sidereal_sun_lon + sidereal_moon_lon)
    return yogas[int(total / (360 / 27))]

def compute_karana(tithi_num): return karanas[(tithi_num * 2 - 1) % 7]

def moon_phase_events(dt_local):
    phase_func = moon_phases(eph)
    t0_utc, t1_utc = get_utc_times_for_local_day(dt_local)
    t0, t1 = ts.from_datetime(t0_utc), ts.from_datetime(t1_utc)
    times, events = find_discrete(t0, t1, phase_func)
    phase_map = {0:"New Moon",1:"First Quarter",2:"Full Moon",3:"Last Quarter"}
    return [(phase_map.get(e,f"Phase {e}"), to_ist(t.utc_datetime().replace(tzinfo=ZoneInfo("UTC"))))
            for t,e in zip(times,events)]

def get_festivals(dt, tithi_num, nakshatra):
    festivals = []
    if tithi_num == 15 and nakshatra == "Punarvasu": festivals.append("Guru Purnima")
    if tithi_num == 1 and nakshatra == "Ashwini": festivals.append("Pahela Boishakh")
    try:
        hijri_date = Gregorian(dt.year, dt.month, dt.day).to_hijri()
        if (hijri_date.month,hijri_date.day)==(10,1): festivals.append("Eid ul-Fitr")
        if (hijri_date.month,hijri_date.day)==(12,10): festivals.append("Eid ul-Adha")
        if hijri_date.month==1 and hijri_date.day==1: festivals.append("Islamic New Year")
    except: pass
    if dt.month==12 and dt.day==25: festivals.append("Christmas")
    return festivals if festivals else ["None"]

def compute_bengali_year(dt_local):
    # Pohela Boishakh falls on 14 April (sometimes 15 April in leap years)
    pohela_boishakh = datetime(dt_local.year, 4, 14, tzinfo=ZoneInfo(timezone_str))
    if dt_local >= pohela_boishakh:
        bengali_year = dt_local.year - 593
    else:
        bengali_year = dt_local.year - 594
    return bengali_year

def compute_bengali_month_day(dt_local):
    AYANAMSHA = 24.25
    def sidereal_sun_lon_on_date(d):
        sunrise, _ = get_sunrise_sunset(d)
        if sunrise is None:
            sunrise = datetime(d.year, d.month, d.day, 6, tzinfo=ZoneInfo(timezone_str))
        t = ts.from_datetime(to_utc(sunrise))
        tropical_lon = earth.at(t).observe(sun).apparent().ecliptic_latlon()[1].degrees
        return normalize_angle(tropical_lon - AYANAMSHA)
    current_sun_lon = sidereal_sun_lon_on_date(dt_local)
    rashi_index = int(current_sun_lon // 30)
    bengali_month = bengali_months[rashi_index]
    # find previous Sankranti
    month_start_date = dt_local
    for i in range(1,50):
        check_date = dt_local - timedelta(days=i)
        check_lon = sidereal_sun_lon_on_date(check_date)
        if int(check_lon // 30) != rashi_index:
            month_start_date = check_date + timedelta(days=1)
            break
    bengali_day = (dt_local.date()-month_start_date.date()).days+1
    return bengali_month, bengali_day

# ---------------- ECLIPSE DETECTION ----------------
def detect_eclipses(dt_local):
    results = []
    t0_utc, t1_utc = get_utc_times_for_local_day(dt_local)
    t0, t1 = ts.from_datetime(t0_utc), ts.from_datetime(t1_utc)
    step = 5  # minutes
    t_list = [t0 + i*(step/(24*60)) for i in range(int((t1-t0)*24*60/step))]
    min_sep = 999
    eclipse_type = None
    in_eclipse = False
    start = max_ecl = end = None
    for t in t_list:
        obs = (earth + location).at(t)
        sun_app, moon_app = obs.observe(sun).apparent(), obs.observe(moon).apparent()
        sun_alt, _, _ = sun_app.altaz()
        moon_alt, _, _ = moon_app.altaz()
        sep = sun_app.separation_from(moon_app).degrees
        # Solar
        if sep < 0.5 and sun_alt.degrees > 0 and moon_alt.degrees > 0:
            if not in_eclipse:
                start = to_ist(t.utc_datetime()); in_eclipse=True; eclipse_type="Solar Eclipse"
            if sep < min_sep: min_sep=sep; max_ecl=to_ist(t.utc_datetime())
        else:
            if in_eclipse and eclipse_type=="Solar Eclipse":
                end = to_ist(t.utc_datetime())
                results.append((eclipse_type,start,max_ecl,end))
                in_eclipse=False; min_sep=999
        # Lunar
        earth_shadow_radius = 0.7
        if sep < earth_shadow_radius and moon_alt.degrees > 0:
            if not in_eclipse:
                start = to_ist(t.utc_datetime()); in_eclipse=True; eclipse_type="Lunar Eclipse"
            if sep < min_sep: min_sep=sep; max_ecl=to_ist(t.utc_datetime())
        else:
            if in_eclipse and eclipse_type=="Lunar Eclipse":
                end = to_ist(t.utc_datetime())
                results.append((eclipse_type,start,max_ecl,end))
                in_eclipse=False; min_sep=999
    return results

# ---------------- MAIN FUNCTION ----------------
def bengali_panchang(date_input=None):
    dt_local = date_input or datetime.now(ZoneInfo("Asia/Kolkata"))
    sun_lon, moon_lon = sun_longitude(dt_local), moon_longitude(dt_local)
    tithi_num, paksha = compute_tithi(sun_lon, moon_lon)
    nakshatra = compute_nakshatra(moon_lon)
    yoga = compute_yoga(sun_lon, moon_lon)
    karana = compute_karana(tithi_num)
    sunrise, sunset = get_sunrise_sunset(dt_local)
    moonrise, moonset = get_moonrise_moonset(dt_local)
    phases = moon_phase_events(dt_local)
    festivals = get_festivals(dt_local, tithi_num, nakshatra)
    bengali_month, bengali_day = compute_bengali_month_day(dt_local)
    eclipses = detect_eclipses(dt_local)
    bengali_year = compute_bengali_year(dt_local)

    print(f"\n📅 Bengali Panchang for {city}, {state}: ({dt_local.strftime('%A, %d-%m-%Y')}, at {dt_local.strftime('%I:%M %p IST')})")
    print(f"----------------------------")
    print(f"Today (Bengali): {bengali_month} {bengali_day}, {bengali_year} Bangabda")
    print(f"Tithi: {tithi_num} ({paksha} Paksha)")
    print(f"Nakshatra: {nakshatra}")
    print(f"Yoga: {yoga}")
    print(f"Karana: {karana}")
    print(f"----------------------------")
    print(f"Sunrise: {sunrise.strftime('%I:%M %p IST') if sunrise else 'N/A'}")
    print(f"Sunset: {sunset.strftime('%I:%M %p IST') if sunset else 'N/A'}")
    print(f"Moonrise: {moonrise.strftime('%I:%M %p IST') if moonrise else 'N/A'}")
    print(f"Moonset: {moonset.strftime('%I:%M %p IST') if moonset else 'N/A'}")
    print(f"----------------------------")
    print(f"Festivals: {', '.join(festivals)}")
    print(f"----------------------------")
    print("🌙 Moon phases today:")
    if phases:
        for name, when in phases: print(f"{name} at {when.strftime('%I:%M %p IST')}")
    else:
        print("No major moon phase event today !")
    print(f"----------------------------")
    print("🌑 Eclipses visible today:")
    if eclipses:
        for ecl_type,start,max_ecl,end in eclipses:
            print(f"{ecl_type}:")
            print(f"   Start: {start.strftime('%I:%M %p IST')}")
            print(f"   Max:   {max_ecl.strftime('%I:%M %p IST')}")
            print(f"   End:   {end.strftime('%I:%M %p IST')}")
    else:
        print("No eclipse visible today from Agartala")
    print(f"----------------------------")

# ---------------- RUN ----------------
if __name__ == "__main__":
    bengali_panchang()

