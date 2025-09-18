from datetime import datetime, timedelta
from skyfield.api import load, wgs84, N, E
from skyfield.almanac import risings_and_settings, find_discrete, moon_phases
from hijridate import Gregorian
from zoneinfo import ZoneInfo

# ---------------- CONFIG ----------------
latitude = 23.8315
longitude = 91.2868
ts = load.timescale()
eph = load('de421.bsp')
earth, sun, moon = eph['earth'], eph['sun'], eph['moon']
location = wgs84.latlon(latitude * N, longitude * E)

bengali_months = [
    "Boishakh", "Jyoishtho", "Asharh", "Shraban",
    "Bhadro", "Ashwin", "Kartik", "Ogrohayon",
    "Poush", "Magh", "Falgun", "Chaitra"
]

nakshatras = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu",
    "Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra",
    "Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha",
    "Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

karanas = [
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti"
]

# ---------------- HELPERS ----------------
def to_ist(dt):
    return dt.astimezone(ZoneInfo("Asia/Kolkata"))

def normalize_angle(angle):
    return angle % 360

def get_sunrise_sunset(dt):
    f = risings_and_settings(eph, sun, location)
    t0 = ts.utc(dt.year, dt.month, dt.day, 0)
    t1 = ts.utc(dt.year, dt.month, dt.day, 23, 59)
    times, events = find_discrete(t0, t1, f)
    sunrise = sunset = None
    for t, e in zip(times, events):
        dt_ist = to_ist(t.utc_datetime())
        if e == 1: sunrise = dt_ist
        elif e == 0: sunset = dt_ist
    return sunrise, sunset

def get_moonrise_moonset(dt):
    f = risings_and_settings(eph, moon, location)
    t0 = ts.utc(dt.year, dt.month, dt.day, 0)
    t1 = ts.utc(dt.year, dt.month, dt.day, 23, 59)
    times, events = find_discrete(t0, t1, f)
    moonrise = moonset = None
    for t, e in zip(times, events):
        dt_ist = to_ist(t.utc_datetime())
        if e == 1: moonrise = dt_ist
        elif e == 0: moonset = dt_ist
    return moonrise, moonset

def sun_longitude(dt):
    t = ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    e = earth.at(t)
    return normalize_angle(e.observe(sun).apparent().ecliptic_latlon()[1].degrees)

def moon_longitude(dt):
    t = ts.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    e = earth.at(t)
    return normalize_angle(e.observe(moon).apparent().ecliptic_latlon()[1].degrees)

def compute_tithi(sun_lon, moon_lon):
    angle = normalize_angle(moon_lon - sun_lon)
    tithi_num = int(angle // 12) + 1
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    if tithi_num > 15: tithi_num -= 15
    return tithi_num, paksha

def compute_nakshatra(moon_lon):
    idx = int((moon_lon / 360) * 27)
    return nakshatras[idx]

def compute_yoga(sun_lon, moon_lon):
    total = normalize_angle(sun_lon + moon_lon)
    idx = int(total / (360 / 27))
    return nakshatras[idx]

def compute_karana(tithi_num):
    idx = (tithi_num * 2 - 1) % 7
    return karanas[idx]

def eclipses_today(dt):
    t0 = ts.utc(dt.year, dt.month, dt.day, 0)
    t1 = ts.utc(dt.year, dt.month, dt.day, 23, 59)
    phase_func = moon_phases(eph)
    times, events = find_discrete(t0, t1, phase_func)
    eclipse_events = []
    for t, e in zip(times, events):
        dt_ist = to_ist(t.utc_datetime())
        if e == 0:
            start = dt_ist - timedelta(minutes=30)
            maximum = dt_ist
            end = dt_ist + timedelta(minutes=30)
            eclipse_events.append(("Solar Eclipse", start, maximum, end))
        elif e == 2:
            start = dt_ist - timedelta(minutes=30)
            maximum = dt_ist
            end = dt_ist + timedelta(minutes=30)
            eclipse_events.append(("Lunar Eclipse", start, maximum, end))
    return eclipse_events

def get_festivals(dt, tithi_num, nakshatra):
    festivals = []
    if tithi_num == 15 and nakshatra == "Punarvasu":
        festivals.append("Guru Purnima")
    if tithi_num == 1 and nakshatra == "Ashwini":
        festivals.append("Pahela Boishakh")
    hijri_date = Gregorian(dt.year, dt.month, dt.day).to_hijri()
    if (hijri_date.month, hijri_date.day) == (10,1):
        festivals.append("Eid ul-Fitr")
    if (hijri_date.month, hijri_date.day) == (12,10):
        festivals.append("Eid ul-Adha")
    if hijri_date.month == 1 and hijri_date.day == 1:
        festivals.append("Islamic New Year")
    if dt.month == 12 and dt.day == 25:
        festivals.append("Christmas")
    return festivals if festivals else ["None"]

def compute_bengali_month_day(dt):
    sunrise, _ = get_sunrise_sunset(dt)
    if sunrise is None:
        sunrise = datetime(dt.year, dt.month, dt.day, 6)
    sun_lon = sun_longitude(sunrise)
    rashi_index = int(sun_lon // 30)
    bengali_month = bengali_months[rashi_index]
    for i in range(0, 35):
        check_date = dt - timedelta(days=i)
        check_sun_lon = sun_longitude(get_sunrise_sunset(check_date)[0] or datetime(check_date.year, check_date.month, check_date.day, 6))
        if int(check_sun_lon // 30) == rashi_index:
            month_start = check_date
            break
    bengali_day = (dt.date() - month_start.date()).days + 1
    return bengali_month, bengali_day

# ---------------- MAIN FUNCTION ----------------
def bengali_panchang(date_input=None):
    dt = date_input or datetime.now()
    sun_lon, moon_lon = sun_longitude(dt), moon_longitude(dt)
    tithi_num, paksha = compute_tithi(sun_lon, moon_lon)
    nakshatra = compute_nakshatra(moon_lon)
    yoga = compute_yoga(sun_lon, moon_lon)
    karana = compute_karana(tithi_num)
    sunrise, sunset = get_sunrise_sunset(dt)
    moonrise, moonset = get_moonrise_moonset(dt)
    eclipse_events = eclipses_today(dt)
    festivals = get_festivals(dt, tithi_num, nakshatra)
    bengali_month, bengali_day = compute_bengali_month_day(dt)

    print(f"\n📅 Bengali Panchang for Agartala, Tripura: ({dt.strftime('%A, %d-%m-%Y')})")
    print(f"----------------------------")
    print(f"Today(Bengali): {bengali_month}, {bengali_day}")
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
    print("🌑 Eclipse Info:")
    if eclipse_events:
        for kind, start, maximum, end in eclipse_events:
            print(f"{kind}: Start {start.strftime('%I:%M %p IST')}, Max {maximum.strftime('%I:%M %p IST')}, End {end.strftime('%I:%M %p IST')}")
    else:
        print("No eclipses today")
    print(f"----------------------------")

# ---------------- RUN ----------------
if __name__ == "__main__":
    bengali_panchang()
