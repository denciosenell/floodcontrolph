import re
import pandas as pd
import folium
from bs4 import BeautifulSoup

# === File Settings ===
DOM_FILE = "resources/all_national_data.txt"
MAP_FILE = "index.html"
EXCEL_FILE = "output/national_projects_data.xlsx"

# === Function to extract coordinates from location string. ===
def extract_coordinates(location_string):
    match = re.search(r'\(([-+]?[0-9]*\.?[0-9]+)\s*,\s*([-+]?[0-9]*\.?[0-9]+)\)', location_string)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

# === Load HTML ===
with open(DOM_FILE, "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()
soup = BeautifulSoup(html, "html.parser")

# === Extract projects ===
rows = soup.select("tr td.desc-a a.load-project-card")
templates = {t["id"]: t for t in soup.select("template[id^='proj-card-']")}
projects = []

for row in rows:
    project_id = row.get("data-id")
    project_name = row.get_text(strip=True)
    template_tag = templates.get(f"proj-card-{project_id}")
    if not template_tag:
        continue

    template_soup = BeautifulSoup(template_tag.decode_contents(), "html.parser")
    location_tag = template_soup.select_one("div.longi span")
    location_string = location_tag.get_text(strip=True) if location_tag else "Unknown"
    latitude, longitude = extract_coordinates(location_string)

    contractor_tag = template_soup.select_one("div.contractor p")
    cost_tag = template_soup.select_one("div.const span")
    start_date_tag = template_soup.select_one("div.start-date span")

    contractor = contractor_tag.get_text(strip=True) if contractor_tag else "N/A"
    cost_str = cost_tag.get_text(strip=True).replace(",", "").replace("₱", "") if cost_tag else "0"
    cost = float(cost_str) if cost_str.replace(".", "", 1).isdigit() else 0
    start_date = start_date_tag.get_text(strip=True) if start_date_tag else "Unknown"

    if latitude is not None and longitude is not None:
        projects.append({
            "Title": project_name,
            "Contractor": contractor,
            "Start Date": start_date,
            "Cost": cost,
            "Latitude": latitude,
            "Longitude": longitude,
            "Location": location_string
        })

df = pd.DataFrame(projects)
print(f"✅ Total projects: {len(df)}")

# === Optional: export to Excel ===
#df.to_excel(EXCEL_FILE, index=False)
#print(f"✅ Projects exported to '{EXCEL_FILE}'")

# === Define color based on cost ===
def get_color(cost):
    if cost < 50_000_000:
        return "grey"
    elif 50_000_000 <= cost < 100_000_000:
        return "yellow"
    elif 100_000_000 <= cost < 200_000_000:
        return "orange"
    elif cost >= 200_000_000:
        return "red"
    else:
        return "black"

# === Create map ===
map_center = [11.5531, 124.7341]
project_map = folium.Map(location=map_center, zoom_start=6, control_scale=True)


# === Feature groups for checkboxes ===
'''groups = {
    "<50M": folium.FeatureGroup(name="<50M", show=False),
    "50M–100M": folium.FeatureGroup(name="50M–100M"),
    "100M–200M": folium.FeatureGroup(name="100M–200M"),
    "200M–300M": folium.FeatureGroup(name="200M–300M"),
    "300M–400M": folium.FeatureGroup(name="300M–400M"),
    "400M+": folium.FeatureGroup(name="400M+"),
}'''
groups = {
    "<50M": folium.FeatureGroup(name="<50M", show=False),
    "50M–100M": folium.FeatureGroup(name="50M–100M"),
    "100M–200M": folium.FeatureGroup(name="100M–200M"),
    "200M+": folium.FeatureGroup(name="200M+"),
}

# === Add pins to feature groups ===
for idx, row in df.iterrows():
    cost = row["Cost"]
    contractor = row["Contractor"]
    color = get_color(cost)
    #popup_html = f"<b>{row['Title']}</b><br>Cost: ₱{cost:,.0f}"

    popup_html = f"""
    <b>{row['Title']}</b><br>
    Contractor: {contractor}<br>
    Start Date: {row['Start Date']} Cost: <span style="color:red; font-size:14px; font-weight:bold;">₱{cost:,.0f}</span>
    """

    marker = folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=8,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        tooltip=f"₱{cost:,.0f}"
    ).add_child(folium.Popup(popup_html, max_width=300))

    # Assign marker to proper group
    if cost < 50_000_000:
        groups["<50M"].add_child(marker)
    elif 50_000_000 <= cost < 100_000_000:
        groups["50M–100M"].add_child(marker)
    elif 100_000_000 <= cost < 200_000_000:
        groups["100M–200M"].add_child(marker)
    elif cost >= 200_000_000:
        groups["200M+"].add_child(marker)

# Add all feature groups to map
for group in groups.values():
    group.add_to(project_map)

# === Add LayerControl for checkboxes ===
folium.LayerControl(collapsed=False).add_to(project_map)

# === Add legend ===
legend_html = """
<div style="position: fixed; bottom: 30px; left: 30px; width: 100px; height: 100px;
     background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
     padding: 5px; border-radius: 5px;">
<b> Project Cost </b><br>
<i style="background: grey; width: 10px; height: 10px; display:inline-block; margin-right:1px;"></i> <50M<br>
<i style="background: yellow; width: 10px; height: 10px; display:inline-block; margin-right:1x;"></i> 50M–100M<br>
<i style="background: orange; width: 10px; height: 10px; display:inline-block; margin-right:1px;"></i> 100M–200M<br>
<i style="background: red; width: 10px; height: 10px; display:inline-block; margin-right:1px;"></i> 200M up<br>
</div>
"""
project_map.get_root().html.add_child(folium.Element(legend_html))

# tooltip size
style_html = """
<style>
.leaflet-tooltip {
    font-size: 20px !important;
    font-weight: bold !important;
    color: black !important;
}
</style>
"""
project_map.get_root().html.add_child(folium.Element(style_html))

# TITLE
title_html = """
<div style="
    position: fixed;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    border-radius: 5px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
">
<span style="font-size: 14px; font-weight: bold;">National Flood Control Projects (2020–2024)</span>
<span style="font-size: 10px; font-weight: normal;">Data from sumbongsapangulo.ph</span>
</div>
"""
project_map.get_root().html.add_child(folium.Element(title_html))
# === Save map ===
project_map.save(MAP_FILE)
print(f"✅ Map with colored pins and checkboxes saved as '{MAP_FILE}'")
