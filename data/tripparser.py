import xml.etree.cElementTree as et
from pathlib import Path

base_path = Path().absolute()
# set path to the OpenBerlinScenario.xml
client_path = base_path.joinpath("berlin-v5.4-1pct.plans.xml")
# read client data 
client_data = et.parse(client_path)

root = et.Element('root')

print("Start building XML")
for client in client_data.getroot().iterfind('person'):
    client_id = client.get("id")
    plan = client.find("plan")
    # person = et.Element("person", id= client_id)
    person = et.SubElement(root, "person", id= client_id)
    start = plan.find('activity')
    et.SubElement(person, 'trip', x = start.attrib['x'], y = start.attrib['y'], trav_time = "0")
    for activity, leg in zip(plan.findall('activity')[1:], plan.findall('leg')):
        x = activity.attrib['x']
        y = activity.attrib['y']
        route = leg.find('route')
        trav_time = route.attrib['trav_time']
        et.SubElement(person, 'trip', x = x, y = y, trav_time = trav_time)
trip_tree = et.ElementTree(root)
print("Savig XML")
trip_tree.write("reduced_berlin_v5.4-1pct.plans.xml")
print("Done")