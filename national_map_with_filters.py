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
    "QM CORP": folium.FeatureGroup(name="QM CORP"),
    "ZALDY CO": folium.FeatureGroup(name="ZALDY CO"),
    "DISCAYA": folium.FeatureGroup(name="DISCAYA"),
    "LEGACY": folium.FeatureGroup(name="LEGACY"),

}

# === Add pins to feature groups ===
# Keywords to check for black outline
QM_CORP = ["QM BUILDER", "QUIRANTE", "QG", "Adamant"]
CO_CORP = ["SUNWEST", "HI-TONE"]
DISCAYA = ["ST. TIMOTHY", "ST. GERRARD", "ALPHA & OMEGA", "ST. MATTHEW"]
LEGACY = ["LEGACY CONSTRUCTION"]
for idx, row in df.iterrows():
    cost = row["Cost"]
    contractor = row["Contractor"].upper()  # Make comparison case-insensitive
    color = get_color(cost)

    # Check if contractor name starts with any of the keywords
    if any(contractor.startswith(keyword) for keyword in QM_CORP):
        border_color = "black"
        border_weight = 2
    elif any(contractor.startswith(keyword) for keyword in CO_CORP):
        border_color = "blue"
        border_weight = 2
    elif any(contractor.startswith(keyword) for keyword in DISCAYA):
        border_color = "red"
        border_weight = 2
    elif any(contractor.startswith(keyword) for keyword in LEGACY):
        border_color = "green"
        border_weight = 2
    else:
        border_color = color
        border_weight = 1  # default thin border

    popup_html = f"""
    <b>{row['Title']}</b><br>
    Contractor: {row['Contractor']}<br>
    Start Date: {row['Start Date']}<br>
    Cost: <span style="color:red; font-size:14px; font-weight:bold;">₱{cost:,.0f}</span><br>
    <a href='https://www.google.com/maps?q={row['Latitude']},{row['Longitude']}'
       target='_blank' style="color:#1a73e8; text-decoration:none; font-weight:bold;">
       📍 View on Google Maps
    </a>
    """

    marker = folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=8,
        color=border_color,  # border color
        weight=border_weight,  # border thickness
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        tooltip=folium.Tooltip(
            f"<div style='text-align:center; max-width:600px; white-space: normal;'>"
            f"<span style='color:red; font-weight:bold; font-size:14px;'>₱{cost:,.0f}</span><br>"
            f"<span style='font-size:10px;'>{row['Contractor'][:21]}</span><br>"
            f"<span style='font-size:10px;'>{row['Start Date']}</span>"
            f"</div>",

            sticky=True
        ),
        popup=folium.Popup(popup_html, max_width=600)
    )

    # Assign marker to proper group
    if any(contractor.startswith(keyword) for keyword in QM_CORP):
        groups["QM CORP"].add_child(marker)
    elif any(contractor.startswith(keyword) for keyword in CO_CORP):
        groups["ZALDY CO"].add_child(marker)
    elif any(contractor.startswith(keyword) for keyword in DISCAYA):
        groups["DISCAYA"].add_child(marker)
    elif any(contractor.startswith(keyword) for keyword in LEGACY):
        groups["LEGACY"].add_child(marker)
    elif cost < 50_000_000:
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

# === Colored squares beside each checkbox ===
style_js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    const layerItems = document.querySelectorAll('.leaflet-control-layers-selector');

    layerItems.forEach(function(item) {
        const label = item.nextSibling;  // text node after checkbox
        if (!label) return;
        const name = label.textContent.trim();

        // Create color square
        const colorBox = document.createElement('span');
        colorBox.style.display = 'inline-block';
        colorBox.style.width = '12px';
        colorBox.style.height = '12px';
        colorBox.style.marginLeft = '6px';
        colorBox.style.marginRight = '3px';
        colorBox.style.border = '1px solid black';
        colorBox.style.verticalAlign = 'middle';

        // Match color depending on layer name
        if (name.includes('<50M')) colorBox.style.background = 'grey';
        else if (name.includes('50M')) colorBox.style.background = 'yellow';
        else if (name.includes('100M')) colorBox.style.background = 'orange';
        else if (name.includes('200M')) colorBox.style.background = 'red';
        else if (name.includes('QM')) { colorBox.style.background = 'white'; colorBox.style.border = '2px solid black'; }
        else if (name.includes('ZALDY')) { colorBox.style.background = 'white'; colorBox.style.border = '2px solid blue'; }
        else if (name.includes('DISCAYA')) { colorBox.style.background = 'white'; colorBox.style.border = '2px solid red'; }
        else if (name.includes('LEGACY')) { colorBox.style.background = 'white'; colorBox.style.border = '2px solid green'; }

        // Insert before label text
        label.parentNode.insertBefore(colorBox, label);
    });
});
</script>
"""

project_map.get_root().html.add_child(folium.Element(style_js))

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
