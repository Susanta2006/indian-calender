from datetime import datetime, timedelta
from skyfield.api import load, wgs84
from skyfield.almanac import risings_and_settings, find_discrete, moon_phases
from hijridate import Gregorian
from zoneinfo import ZoneInfo
import pyfiglet
import warnings
import geocoder
import numpy as np
#import timezonefinder

############################# BANNER #############################
banner_text = pyfiglet.figlet_format("Ind-Panchang")
print(banner_text, "\n version 2.0 (All Festivals)")
warnings.filterwarnings("ignore")
##################################################################
print("(50% MY LOGIC <--> 50% PROMPT. ENGG.)")
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

try:
    g = geocoder.ip("me")  # auto-detect location by IP
    if g.ok and g.latlng:
        latitude, longitude = g.latlng
        city = g.city if g.city else "Unknown City"
        state = g.state if g.state else "Unknown State"
        """
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=longitude, lat=latitude)
        if not timezone_str:
            timezone_str = "Asia/Kolkata"  # fallback
        """
    else:
        # fallback (Agartala if detection fails)
        latitude, longitude = 23.8315, 91.2868
        city, state = "Agartala", "Tripura"
        """
        timezone_str = "Asia/Kolkata"
        """
except Exception:
    # fallback on any error
    latitude, longitude = 23.8315, 91.2868
    city, state = "Agartala", "Tripura"
    #timezone_str = "Asia/Kolkata"

ts = load.timescale()
eph = load("de421.bsp")
earth, sun, moon = eph["earth"], eph["sun"], eph["moon"]
location = wgs84.latlon(latitude, longitude)
ZONE = "Asia/Kolkata"

bengali_months = [
    "Boishakh", "Jyoishtho", "Asharh", "Shraban", "Bhadro", "Ashwin",
    "Kartik", "Ogrohayon", "Poush", "Magh", "Falgun", "Chaitra"
]

lunar_months = [
    "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada", "Ashwin",
    "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna", "Chaitra"
]

nakshatras = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra", "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

yogas = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarman", "Dhriti", "Shula",
    "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana",
    "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti"
]

karanas = ["Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti"]

# ---------------- HELPERS ----------------

def to_ist(dt):
    return dt.astimezone(ZoneInfo(ZONE))

def to_utc(dt):
    return dt.astimezone(ZoneInfo("UTC"))

def normalize_angle(angle):
    return angle % 360

def get_utc_times_for_local_day(dt_local):
    local_zone = ZoneInfo(ZONE)
    start_of_day = datetime(dt_local.year, dt_local.month, dt_local.day, 0, 0, tzinfo=local_zone)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
    return start_of_day.astimezone(ZoneInfo("UTC")), end_of_day.astimezone(ZoneInfo("UTC"))

# ---------------- PANCHANG CALCULATIONS ----------------

def get_sunrise_sunset(dt_local):
    f = risings_and_settings(eph, sun, location)
    t0_utc, t1_utc = get_utc_times_for_local_day(dt_local)
    t0, t1 = ts.from_datetime(t0_utc), ts.from_datetime(t1_utc)
    times, events = find_discrete(t0, t1, f)
    sunrise = sunset = None
    for t, e in zip(times, events):
        if e in (True, 1):
            sunrise = to_ist(t.utc_datetime().replace(tzinfo=ZoneInfo("UTC")))
        else:
            sunset = to_ist(t.utc_datetime().replace(tzinfo=ZoneInfo("UTC")))
    return sunrise, sunset

def get_moonrise_moonset(dt_local):
    f = risings_and_settings(eph, moon, location)
    t0_utc, t1_utc = get_utc_times_for_local_day(dt_local)
    t0, t1 = ts.from_datetime(t0_utc), ts.from_datetime(t1_utc)
    times, events = find_discrete(t0, t1, f)
    moonrise = moonset = None
    for t, e in zip(times, events):
        if e in (True, 1):
            moonrise = to_ist(t.utc_datetime().replace(tzinfo=ZoneInfo("UTC")))
        else:
            moonset = to_ist(t.utc_datetime().replace(tzinfo=ZoneInfo("UTC")))
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

def get_tithi_events(dt_local):
    """
    Calculates tithi transitions for the day.
    Searches a wide window to capture Tithis that span across midnight.
    """
    local_zone = ZoneInfo(ZONE)
    # Search a window from noon yesterday to noon tomorrow
    t_start = datetime(dt_local.year, dt_local.month, dt_local.day, 12, tzinfo=local_zone) - timedelta(days=1)
    t_end = t_start + timedelta(days=2)
    
    t0, t1 = ts.from_datetime(to_utc(t_start)), ts.from_datetime(to_utc(t_end))

    def tithi_index(t):
        t = np.atleast_1d(t)
        sun_lons = np.array([earth.at(time_obj).observe(sun).apparent().ecliptic_latlon()[1].degrees for time_obj in t])
        moon_lons = np.array([earth.at(time_obj).observe(moon).apparent().ecliptic_latlon()[1].degrees for time_obj in t])
        angle = normalize_angle(moon_lons - sun_lons)
        return np.floor((angle + 1e-9) / 12)

    tithi_index.step_days = 0.25
    times, indices = find_discrete(t0, t1, tithi_index)
    
    results = []
    
    # Find the index of the Tithi active at the start of the local day
    today_start_utc = to_utc(datetime(dt_local.year, dt_local.month, dt_local.day, tzinfo=local_zone))
    idx_start = np.searchsorted(times.utc_datetime(), today_start_utc) - 1
    if idx_start < 0:
        idx_start = 0

    # Iterate through tithi transitions starting from the one active at the start of the day
    for i in range(idx_start, len(times) - 1):
        t_utc_start = times[i].utc_datetime().replace(tzinfo=ZoneInfo("UTC"))
        t_ist_start = to_ist(t_utc_start)
        
        t_utc_end = times[i+1].utc_datetime().replace(tzinfo=ZoneInfo("UTC"))
        t_ist_end = to_ist(t_utc_end)

        # Check if the event's start or end is on the current local date
        if t_ist_start.date() == dt_local.date() or t_ist_end.date() == dt_local.date():
            tithi_num_raw = indices[i] + 1
            paksha = "Shukla" if tithi_num_raw <= 15 else "Krishna"
            tithi_num = tithi_num_raw - 15 if tithi_num_raw > 15 else tithi_num_raw
            
            results.append({
                "tithi_num": int(tithi_num),
                "paksha": paksha,
                "start": t_ist_start,
                "end": t_ist_end
            })

    return results

def moon_phase_events(dt_local):
    phase_func = moon_phases(eph)
    t0_utc, t1_utc = get_utc_times_for_local_day(dt_local)
    t0, t1 = ts.from_datetime(t0_utc), ts.from_datetime(t1_utc)
    times, events = find_discrete(t0, t1, phase_func)
    phase_map = {0: "New Moon", 1: "First Quarter", 2: "Full Moon", 2: "Full Moon", 3: "Last Quarter"}
    return [(phase_map.get(e, f"Phase {e}"), to_ist(t.utc_datetime().replace(tzinfo=ZoneInfo("UTC")))) for t, e in zip(times, events)]


def compute_bengali_year(dt_local):
    pohela_boishakh = datetime(dt_local.year, 4, 14, tzinfo=ZoneInfo(ZONE))
    return dt_local.year - 593 if dt_local >= pohela_boishakh else dt_local.year - 594

def compute_bengali_month_day(dt_local, return_rashi_index=False):
    AYANAMSHA = 24.25
    def sidereal_sun_lon_on_date(d):
        sunrise, _ = get_sunrise_sunset(d)
        if sunrise is None:
            sunrise = datetime(d.year, d.month, d.day, 6, tzinfo=ZoneInfo(ZONE))
        t = ts.from_datetime(to_utc(sunrise))
        tropical_lon = earth.at(t).observe(sun).apparent().ecliptic_latlon()[1].degrees
        return normalize_angle(tropical_lon - AYANAMSHA)

    current_sun_lon = sidereal_sun_lon_on_date(dt_local)
    rashi_index = int(current_sun_lon // 30)
    bengali_month = bengali_months[rashi_index]
    
    month_start_date = dt_local
    for i in range(1, 50):
        check_date = dt_local - timedelta(days=i)
        check_lon = sidereal_sun_lon_on_date(check_date)
        if int(check_lon // 30) != rashi_index:
            month_start_date = check_date + timedelta(days=1)
            break
    bengali_day = (dt_local.date() - month_start_date.date()).days + 1
    
    if return_rashi_index:
        return bengali_month, bengali_day, rashi_index
    return bengali_month, bengali_day

# ---------------- ECLIPSE DETECTION ----------------
def detect_eclipses(dt_local):
    results = []
    t0_utc, t1_utc = get_utc_times_for_local_day(dt_local)
    t0, t1 = ts.from_datetime(t0_utc), ts.from_datetime(t1_utc)

    # --- Solar Eclipse Function ---
    def is_solar_eclipse(t):
        e = earth.at(t)
        s = e.observe(sun).apparent()
        m = e.observe(moon).apparent()
        obs = (earth + location).at(t)
        s_alt, _, _ = obs.observe(sun).apparent().altaz()
        # Use bitwise '&' for array comparison, not 'and'
        return (s.separation_from(m).degrees < 0.5) & (s_alt.degrees > 0)
    
    is_solar_eclipse.step_days = 1 / (24 * 60)

    # --- Lunar Eclipse Function ---
    def is_lunar_eclipse(t):
        e = earth.at(t)
        s = e.observe(sun).apparent()
        m = e.observe(moon).apparent()
        obs = (earth + location).at(t)
        m_alt, _, _ = obs.observe(moon).apparent().altaz()
        # Use bitwise '&' for array comparison, not 'and'
        return (s.separation_from(m).degrees > 179.5) & (m_alt.degrees > 0)

    is_lunar_eclipse.step_days = 1 / (24 * 60)

    # --- Find Events ---
    times, events = find_discrete(t0, t1, is_solar_eclipse)
    if len(events) > 1 and 1 in events:
        start_time = to_ist(times[events == 1][0].utc_datetime())
        end_time = to_ist(times[events == 1][-1].utc_datetime())
        max_time = start_time + (end_time - start_time) / 2
        results.append(("Solar Eclipse", start_time, max_time, end_time))

    times, events = find_discrete(t0, t1, is_lunar_eclipse)
    if len(events) > 1 and 1 in events:
        start_time = to_ist(times[events == 1][0].utc_datetime())
        end_time = to_ist(times[events == 1][-1].utc_datetime())
        max_time = start_time + (end_time - start_time) / 2
        results.append(("Lunar Eclipse", start_time, max_time, end_time))
        
    return results

# ---------------- FESTIVAL RULES ----------------
def get_festivals(dt, lunar_month=None, paksha=None, tithi_num=None, nakshatra=None):
    festivals = []
    m, d = dt.month, dt.day
    # Tithi-based festivals
    if lunar_month and paksha and tithi_num:
        if lunar_month == "Chaitra" and paksha == "Shukla" and tithi_num == 9: festivals.append("Ram Navami")
        if lunar_month == "Vaishakha" and paksha == "Shukla" and tithi_num == 15: festivals.append("Buddha Purnima")
        if lunar_month == "Ashadha" and paksha == "Shukla" and tithi_num == 15 and nakshatra == "Punarvasu": festivals.append("Guru Purnima")
        if lunar_month == "Shravana" and paksha == "Shukla" and tithi_num == 15: festivals.append("Raksha Bandhan")
        if lunar_month == "Shravana" and paksha == "Krishna" and tithi_num == 8: festivals.append("Janmashtami")
        if lunar_month == "Bhadrapada" and paksha == "Shukla" and tithi_num == 4: festivals.append("Ganesh Chaturthi")
        if lunar_month == "Bhadrapada" and paksha == "Krishna" and tithi_num == 11: festivals.append("Vishwakarma Puja")
        if lunar_month == "Ashwin" and paksha == "Krishna" and tithi_num == 15: festivals.append("Mahalaya")
        if lunar_month == "Ashwin" and paksha == "Shukla" and tithi_num == 4: festivals.append("Durga Puja (Begains)")
        if lunar_month == "Ashwin" and paksha == "Shukla" and tithi_num == 5: festivals.append("Durga Puja (Panchami)")
        if lunar_month == "Ashwin" and paksha == "Shukla" and tithi_num == 6: festivals.append("Durga Puja (Sosthi)")
        if lunar_month == "Ashwin" and paksha == "Shukla" and tithi_num == 7: festivals.append("Durga Puja (Saptami)")
        if lunar_month == "Ashwin" and paksha == "Shukla" and tithi_num == 8: festivals.append("Durga Puja (Astami)")
        if lunar_month == "Ashwin" and paksha == "Shukla" and tithi_num == 9: festivals.append("Durga Puja (Navami)")
        if lunar_month == "Ashwin" and paksha == "Shukla" and tithi_num == 10: festivals.append("Dussehra / Vijaya Dashami")
        if lunar_month == "Kartika" and paksha == "Krishna" and tithi_num == 14: festivals.append("Chhoti Diwali / Naraka Chaturdashi")
        if lunar_month == "Kartika" and paksha == "Krishna" and tithi_num == 15: festivals.append("Diwali")
        if lunar_month == "Magha" and paksha == "Krishna" and tithi_num == 14: festivals.append("Maha Shivaratri")
        if lunar_month == "Phalguna" and paksha == "Krishna" and tithi_num == 15: festivals.append("Holika Dahan")
        if lunar_month == "Phalguna" and paksha == "Shukla" and tithi_num == 1: festivals.append("Holi")
    # Date-based festivals
    if m == 1 and d == 14: festivals.append("Makar Sankranti / Pongal")
    if m == 3 and d in [22, 23]: festivals.append("Ugadi / Gudi Padwa")
    if m == 4 and d == 14: festivals.append("Pohela Boishakh / Baisakhi / Vishu / Tamil New Year")
    if m == 8 and d in [28, 29]: festivals.append("Onam")
    if m == 12 and d == 25: festivals.append("Christmas")
    if m == 1 and d == 1: festivals.append("Gregorian New Year")
    if m == 4 and d == 14: festivals.append("Vaisakhi")
    if m == 11 and d == 24: festivals.append("Guru Nanak Jayanti")
    try:
        hijri_date = Gregorian(dt.year, dt.month, dt.day).to_hijri()
        if (hijri_date.month, hijri_date.day) == (10, 1): festivals.append("Eid ul-Fitr")
        if (hijri_date.month, hijri_date.day) == (12, 10): festivals.append("Eid ul-Adha")
        if hijri_date.month == 1 and hijri_date.day == 1: festivals.append("Islamic New Year")
    except: pass
    return festivals

# ---------------- MONTHLY FESTIVAL FUNCTION ----------------
def get_monthly_festivals(year, month):
    print(f"\n📅 Festivals for {datetime(year, month, 1).strftime('%B %Y')}:")
    print("------------------------------------------")
    start_date = datetime(year, month, 1, tzinfo=ZoneInfo(ZONE))
    if month == 12: end_date = datetime(year + 1, 1, 1, tzinfo=ZoneInfo(ZONE))
    else: end_date = datetime(year, month + 1, 1, tzinfo=ZoneInfo(ZONE))
    
    # Get all tithi events for a wider window to ensure nothing is missed.
    t_start_fetch = start_date - timedelta(days=5)
    t_end_fetch = end_date + timedelta(days=5)
    
    all_tithi_events = []
    current_fetch_date = t_start_fetch
    
    while current_fetch_date < t_end_fetch:
        all_tithi_events.extend(get_tithi_events(current_fetch_date))
        current_fetch_date += timedelta(days=1)
    
    # Now, process and filter unique festival events
    found_festivals = []
    unique_entries = set()
    
    for tithi_event in all_tithi_events:
        # Only process events that start or end within the target month.
        if tithi_event['start'].month != month and tithi_event['end'].month != month:
            continue
            
        lunar_month_at_start = lunar_months[int(normalize_angle(sun_longitude(tithi_event['start']) - 24.25) // 30)]
        paksha = tithi_event['paksha']
        tithi_num = tithi_event['tithi_num']
        nakshatra_at_start = compute_nakshatra(moon_longitude(tithi_event['start']))

        fests = get_festivals(tithi_event['start'], lunar_month_at_start, paksha, tithi_num, nakshatra_at_start)
        
        for fest in fests:
            # Create a unique key to prevent duplicates
            key = (fest, tithi_event['start'], tithi_event['end'])
            if key not in unique_entries:
                found_festivals.append((fest, tithi_event['start'], tithi_event['end']))
                unique_entries.add(key)
                
    # Add date-based festivals
    current_date_solar = start_date
    while current_date_solar < end_date:
        solar_fests = get_festivals(current_date_solar)
        for fest in solar_fests:
            key = (fest, current_date_solar.date())
            if key not in unique_entries:
                found_festivals.append((fest, current_date_solar, current_date_solar))
                unique_entries.add(key)
        current_date_solar += timedelta(days=1)

    # Sort and print
    found_festivals.sort(key=lambda x: x[1])
    
    if found_festivals:
        for fest, start_t, end_t in found_festivals:
            if isinstance(start_t, datetime) and isinstance(end_t, datetime):
                print(f"🎉 {fest} : from --> {start_t.strftime('%d %b, %I:%M:%S %p')} to {end_t.strftime('%d %b, %I:%M:%S %p')}\n")
            else:
                print(f"🎉 {fest}\n")
    else:
        print("No major festivals found for this month.")
    print("------------------------------------------")

# ---------------- MAIN DAILY FUNCTION ----------------
def daily_panchang(date_input=None):
    dt_local = date_input or datetime.now(ZoneInfo(ZONE))
    sun_lon, moon_lon = sun_longitude(dt_local), moon_longitude(dt_local)
    tithi_num_current, paksha = compute_tithi(sun_lon, moon_lon)
    nakshatra = compute_nakshatra(moon_lon)
    yoga = compute_yoga(sun_lon, moon_lon)
    karana = compute_karana(tithi_num_current)
    sunrise, sunset = get_sunrise_sunset(dt_local)
    moonrise, moonset = get_moonrise_moonset(dt_local)
    phases = moon_phase_events(dt_local)
    eclipses = detect_eclipses(dt_local)
    bengali_year = compute_bengali_year(dt_local)
    bengali_month, bengali_day, rashi_index = compute_bengali_month_day(dt_local, return_rashi_index=True)
    lunar_month = lunar_months[rashi_index]
    tithi_events = get_tithi_events(dt_local)

    # --- Collect Festivals for Today ---
    daily_festivals = []
    daily_festivals.extend(get_festivals(dt_local))
    for tithi in tithi_events:
        tithi_fests = get_festivals(dt_local, lunar_month, tithi['paksha'], tithi['tithi_num'], nakshatra)
        daily_festivals.extend(tithi_fests)

    # --- Print Output ---
    print(f"\n📅 Daily Panchang for Agartala,Tripura:")
    print(f"Today (English): {dt_local.strftime('%A, %d-%m-%Y, %I:%M %p IST')}\n")
    print(f"------------------------------------------")
    print(f"Bengali Date: {bengali_month} {bengali_day}, {bengali_year} Bangabda")
    print(f"Paksha: {paksha} Paksha")
    print(f"Current Tithi: {tithi_num_current}")
    if tithi_events:
        for tithi in tithi_events:
            print(f"  → Tithi {tithi['tithi_num']} ({tithi['paksha']} Paksha) runs from {tithi['start'].strftime('%I:%M %p')} to {tithi['end'].strftime('%I:%M %p')}")
    else:
        # Check if the current tithi spans the whole day
        first_tithi_event = get_tithi_events(dt_local - timedelta(days=1))
        found_tithi = False
        if first_tithi_event:
            for tithi in first_tithi_event:
                if tithi['tithi_num'] == tithi_num_current and tithi['paksha'] == paksha:
                    if tithi['end'] > datetime.now(ZoneInfo(ZONE)):
                        print(f"  → Tithi {tithi_num_current} ({paksha} Paksha) began yesterday at {tithi['start'].strftime('%I:%M %p')} and continues through today.")
                        found_tithi = True
                        break
        if not found_tithi:
            print("  → The current Tithi spans the entire day.")
    print(f"------------------------------------------")
    print(f"Nakshatra: {nakshatra} | Yoga: {yoga} | Karana: {karana}")
    print(f"------------------------------------------")
    print(f"☀️ Sunrise: {sunrise.strftime('%I:%M %p') if sunrise else 'N/A'} | Sunset: {sunset.strftime('%I:%M %p') if sunset else 'N/A'}")
    print(f"🌕 Moonrise: {moonrise.strftime('%I:%M %p') if moonrise else 'N/A'} | Moonset: {moonset.strftime('%I:%M %p') if moonset else 'N/A'}")
    print(f"------------------------------------------")
    print("🎉 Festivals Today:")
    if daily_festivals:
        for fest in sorted(list(set(daily_festivals))): print(f"  • {fest}")
    else:
        print("  No major festival today")
    print(f"------------------------------------------")
    print("🌙 Moon Phases Today:")
    if phases:
        for name, when in phases: print(f"  • {name} at {when.strftime('%I:%M %p')}")
    else:
        print("  No major moon phase event today")
    print(f"------------------------------------------")
    print("🌑 Eclipses Visible Today:")
    if eclipses:
        for ecl_type, start, max_ecl, end in eclipses:
            print(f"  • {ecl_type}: Start: {start.strftime('%I:%M %p')}, Max: {max_ecl.strftime('%I:%M %p')}, End: {end.strftime('%I:%M %p')}")
    else:
        print(f"  No eclipse visible from Agartala,Tripura today")
    print(f"------------------------------------------")

# ---------------- RUN ----------------
if __name__ == "__main__":
    # --- Show Today's Detailed Panchang ---
    now = datetime.now(ZoneInfo(ZONE))
    daily_panchang(date_input=now)
    
    # --- Show This Month's Festival List ---
    get_monthly_festivals(now.year, now.month)
