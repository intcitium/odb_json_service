from geopy.geocoders import Nominatim
from apiserver.utils import get_datetime, clean_concat
import time
import click
import requests
import hashlib
from bs4 import BeautifulSoup as bs


def geo_get_hospitals(c):

    # array to hold the location objects representing hospitals
    h = []
    # index to hold the hashed keys to prevent redundancies
    index = []
    # iterate throught the list of countries and get each page of hospitals
    click.echo('[%s_GEO_get_hospitals] %s' % (get_datetime(), c))
    url = "https://www.hospitalsworldguide.com/hospitals-in-%s/" % c
    page = requests.get(url)
    soup = bs(page.content, 'html.parser')
    cities = soup.find_all('div', class_='city')

    for ci in cities:
        cityurl = ci.find(href=True).get('href')
        citypage = requests.get("https://www.hospitalsworldguide.com" + cityurl)
        citysoup = bs(citypage.content, 'html.parser').find_all('div', class_='information_linea')
        for i in citysoup:
            try:
                ExternalLink = i.find_all(href=True)[0].get('href')
                title = i.find_all(href=True)[0].get_text()
                address = i.find_all('div', class_='information_contenido')[0].get_text()
                address = address[:address.find('\xa0')]
                latlong = geo_string(address)
                if latlong:
                    Latitude = latlong.latitude
                    Longitude = latlong.longitude
                else:
                    Latitude = 0.0
                    Longitude = 0.0
            except:
                ExternalLink = "https://www.hospitalsworldguide.com"
                title = "Hosptial in %s" % c
                address = "Unknown address"
                Latitude = 0.0
                Longitude = 0.0

            hash_str = clean_concat(str(ExternalLink + title)).replace(",", "")
            ext_key = hashlib.md5(hash_str.encode()).hexdigest()
            loc = {
                "class_name": "Location",
                "ExternalLink": ExternalLink,
                "title": title,
                "Ext_key": ext_key,
                "icon": "sap-icon://building",
                "Source": "HosptialsWorldGuide",
                "Latitude": Latitude,
                "Longitude": Longitude,
                "description": "Hospital named %s located at %f, %f" % (title, Latitude, Longitude)
            }
            if ext_key not in index:
                h.append(loc)
                index.append(ext_key)
        
    return h
        
def geo_string(loc_string):
    geolocator = Nominatim(user_agent="osint")
    return geolocator.geocode(loc_string)

def get_location(loc_string, db):
    """
    Look up a location based on a location string.
    Use the get_location_by_description to first check the database
    If it doesn't exist then check Nominatim for Open Streets data
    Use the lat long to check if the location exists by using get_location_by_latlon
    Pass the loc_string so that if it exists, the loc_string can be added
    searched
    :param loc_string:
    :param db:
    :return:
    """
    loc = get_location_by_description(loc_string, db)
    if loc == None:
        try:
            time.sleep(1)
            location = geo_string(loc_string)
            if location:
                loc = get_location_by_latlon(location, loc_string, db)
            else:
                loc = None
        except Exception as e:
            loc = None
            if(str(e) == "Service timed out"):
                pass
            else:
                print(str(e))

    return loc


def get_location_by_description(description, db):
    """
    Look up a location in the database based only on its description. I
    :param description:
    :param db:
    :return:
    """
    sql = ('''
    select * from Location where description containstext '{val}'
    ''').format( val=description)
    r = db.client.command(sql)
    if len(r) == 1:
        node = {"attributes": []}
        r = r[0].oRecordData
        for i in r:
            if i in ["key", "title", "group", "icon"]:
                node[i] = r[i]
            else:
                node["attributes"].append(
                    {"label": i, "value": r[i]}
                )
        return node
    else:
        return None


def get_location_by_latlon(location, loc_string, db):
    """

    :param location:
    :param db:
    :return:
    """
    r = db.client.command('''
    select key, class_name, Category, description, Latitude, Longitude, city,
     icon, title from Location where Latitude = %f and Longitude = %f
    ''' % (location.latitude, location.longitude))

    if len(r) == 0:
        node = db.create_node(**{
            "class_name": "Location",
            "title": loc_string,
            "icon": db.ICON_LOCATION,
            "group": "Locations",
            "attributes": [
                {"label": "Created", "value": get_datetime()},
                {"label": "Latitude", "value": location.latitude},
                {"label": "Longitude", "value": location.longitude},
                {"label": "importance", "value": location.raw["importance"]},
                {"label": "Category", "value": location.raw["type"]},
                {"label": "description", "value": "%s %s" % (loc_string, location.address)},
            ]
        })
        return node["data"]
    else:
        new_description = "%s %s" % (r[0].oRecordData["description"], loc_string)
        db.update(class_name="Location", var="description", val=new_description, key=r[0].oRecordData["key"])
        # update the location
        return r
