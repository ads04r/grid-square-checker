from pykml import parser as kmlparse
import json, argparse, sys

class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKCYAN = '\033[96m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'
def convert_geojson_to_wkt(geojson):
	return (json.dumps(geojson).replace(' ', '').replace('],[', ',0 ').replace('[', '').replace(']', '') + ',0').replace('.0,', ',')
def normalise_wkt(wkt):
	ret = []
	for p in wkt.split(' '):
		c = p.split(',')
		if len(c) == 2:
			c.append(0)
		if len(c) != 3:
			continue
		ret.append(f'{float(c[0]):.2f},{float(c[1]):.2f},{float(c[2]):.2f}')
	return ' '.join(ret)

def process(args):

	# Load data into memory

	eamena_data = []
	kml = None

	if args.export:
		export_data = json.load(args.export)
		if 'business_data' in export_data:
			if 'resources' in export_data['business_data']:
				eamena_data = export_data['business_data']['resources']
	if args.kml:
		kml = kmlparse.parse(args.kml).getroot()

	# Organise data ready for analysis

	data = {}

	if not kml is None:
		for elem in kml.Document.Folder.iterdescendants():
			if not elem.tag.endswith('Placemark'):
				continue
			grid_id = str(elem.name).upper()
			coords = ''
			for e in elem.iterdescendants():
				if hasattr(e, 'coordinates'):
					coords = str(e.coordinates).strip()
			if coords == '':
				continue
			coords = normalise_wkt(coords)
			if not grid_id in data:
				data[grid_id] = {'uuid': [], 'coordinates': []}
			if coords in data[grid_id]['coordinates']:
				continue
			data[grid_id]['coordinates'].append(coords)
			if len(data[grid_id]['coordinates']) == 1:
				data[grid_id]['canonical_coordinates'] = data[grid_id]['coordinates'][0]

	for resource in eamena_data:

		uuid = str(resource['resourceinstance']['resourceinstanceid'])
		name = resource['resourceinstance']['name']
		if not isinstance(name, str):
			if isinstance(name, dict):
				if 'en' in name:
					name = name['en']
			if not isinstance(name, str):
				name = ''
		grid_id = name.upper()
		if grid_id == '':
			continue

		if not grid_id in data:
			data[grid_id] = {'uuid': [], 'coordinates': []}
		if len(uuid) > 0:
			if not uuid in data[grid_id]['uuid']:
				data[grid_id]['uuid'].append(uuid)

		for tile in resource['tiles']:
			if not 'data' in tile:
				continue
			if not polygon_uuid in tile['data']:
				continue
			if not 'features' in tile['data'][polygon_uuid]:
				continue
			for geom in tile['data'][polygon_uuid]['features']:
				if not 'geometry' in geom:
					continue
				if not 'coordinates' in geom['geometry']:
					continue
				wkt = normalise_wkt(convert_geojson_to_wkt(geom['geometry']['coordinates']))
				if len(wkt) == 0:
					continue
				if not wkt in data[grid_id]['coordinates']:
					data[grid_id]['coordinates'].append(wkt)

	return data

def build_summary(data):

	warnings = []
	errors = []

	return (warnings, errors)

if __name__ == "__main__":

	parser = argparse.ArgumentParser(prog="grid-square-checker", description="A quick and dirty script to check that the Grid Squares in the EAMENA database are where they should be.", epilog="This code is not guaranteed to work. At all.")
	parser.add_argument('-e', '--export', type=argparse.FileType('r'), help="A Grid Square export file in JSON format, exported from EAMENA using the packages management command with the arguments -o export_business_data -f json -g 77d18973-7428-11ea-b4d0-02e7594ce0a0")
	parser.add_argument('-k', '--kml', type=argparse.FileType('r'), help="The EAMENA grid square reference, in KML format.")
	parser.add_argument('-f', '--fix', action=argparse.BooleanOptionalAction, default=False, help="If this option is used, a fixed version of the export file will be dumped to STDOUT. Be warned that this file may be incomplete if certain issues cannot be fixed, so it should be imported back into the database with caution.")

	args = parser.parse_args()

	polygon_uuid = '7248e0d0-ca96-11ea-a292-02e7594ce0a0'

	warnings, errors = build_summary(process(args))

	print(warnings)
	print(errors)
