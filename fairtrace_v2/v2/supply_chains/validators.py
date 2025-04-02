import json

from django.core.exceptions import ValidationError


def validate_geojson_point_structure(geometry):
    """Validate the structure of a GeoJSON Point geometry."""
    errors = []
    # Check if 'coordinates' key exists within 'geometry'
    if 'coordinates' not in geometry:
        errors.append("Missing 'coordinates' key within 'geometry'")

    # Check if 'coordinates' is a list of length 2
    coordinates = geometry.get('coordinates', [])
    if not (isinstance(coordinates, list) and len(coordinates) == 2):
        errors.append("'coordinates' should be a list of length 2")

    return errors


def validate_geojson_polygon_structure(geometry):
    """Validate the structure of a GeoJSON Polygon geometry."""
    errors = []

    # Check if 'coordinates' key exists within 'geometry'
    if 'coordinates' not in geometry:
        errors.append("Missing 'coordinates' key within 'geometry'")

    # Check if 'coordinates' is a list of lists
    coordinates = geometry.get('coordinates', [])
    if not isinstance(coordinates, list):
        errors.append("'coordinates' should be a list of lists")

    # Check if each coordinate is a list of length 2
    for ring in coordinates:
        if not (isinstance(ring, list) and all(isinstance(coord, list) and len(coord) == 2 for coord in ring)):
            errors.append("Each coordinate should be a list of length 2")

    return errors


def validate_geojson_polygon(json_data, raise_error=True):
    """
    Validate GeoJSON Feature for both Point and Polygon types.

    Example GeoJSON Feature (Point):
    {
        "type": "Feature",
        "properties": {
            "GUID": "AB-NY-KA -1050",
            "province": "Mkoa wa Magharibi",
            "country": "Uganda"
        },
        "geometry": {
            "type": "Point",
            "coordinates": [30.239719, -0.850388]
        }
    }

    Example GeoJSON Feature (Polygon):
    {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-122.801742, 45.48565],
                    [-122.801742, 45.60491],
                    [-122.584762, 45.60491],
                    [-122.584762, 45.48565],
                    [-122.801742, 45.48565]
                ]
            ]
        }
    }
    """

    if not json_data:
        return json_data
    
    errors = []
    try:
        # Parse JSON data
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        
        if not isinstance(data, dict):
            if raise_error:
                raise ValidationError("JSON data should be a dictionary")
            else:
                return False

        # Check if 'type' key exists and has the value 'Feature'
        if 'type' not in data or data['type'] != 'Feature':
            errors.append("Invalid type. It should be 'Feature'")

        # Check if 'geometry' key exists
        if 'geometry' not in data:
            errors.append("Missing 'geometry' key")
        else:
            geometry_type = data['geometry'].get('type', None)

            # Validate Point type
            if geometry_type == 'Point':
                errors.extend(validate_geojson_point_structure(data['geometry']))

            # Validate Polygon type
            elif geometry_type == 'Polygon':
                errors.extend(validate_geojson_polygon_structure(data['geometry']))

            else:
                errors.append("Invalid or unsupported geometry type. It should be 'Point' or 'Polygon'")

    except json.JSONDecodeError:
        errors.append("Invalid JSON")

    if raise_error:
        if errors:
            raise ValidationError(errors)
    else:
        return False if errors else True


def validate_coordinates(json_data, raise_error=True):
    """
    Validate coordinates for both Point and Polygon types.

    - For Point: Ensures the single pair of coordinates is valid.
    - For Polygon: Ensures that each pair of coordinates within the list of rings is valid.

    Coordinates must have:
    - Longitude between -180 and 180.
    - Latitude between -90 and 90.
    """

    if not json_data:
        return json_data
    
    if isinstance(json_data, str):
        json_data = json.loads(json_data)
    if not isinstance(json_data, dict):
        return json_data

    if 'geometry' not in json_data:
        return json_data
    if 'coordinates' not in json_data["geometry"]:
        return json_data
    
    coordinates = json_data["geometry"]["coordinates"]
    geometry_type = json_data["geometry"].get("type", None)

    errors = []

    # Validate coordinates for Point type
    if geometry_type == 'Point':
        # Expecting a single pair [longitude, latitude]
        lon, lat = coordinates
        if not (-180 <= lon <= 180):
            errors.append(f"Longitude {lon} is out of range (-180 to 180)")
        if not (-90 <= lat <= 90):
            errors.append(f"Latitude {lat} is out of range (-90 to 90)")

    # Validate coordinates for Polygon type
    elif geometry_type == 'Polygon':
        # Iterate over each ring and each coordinate pair in the ring
        for ring in coordinates:
            if not isinstance(ring, list):
                errors.append("Each ring in 'coordinates' should be a list")
                continue
            for lon, lat in ring:
                set_error = False
                if not (-90 <= lat <= 90):
                    set_error = True
                if not (-180 <= lon <= 180):
                    set_error = True
                if set_error:
                    errors.append(
                        f"[{lon}, {lat}]: "
                        f"Longitude must be between -180 and 180, "
                        f"Latitude must be between -90 and 90."
                    )

    else:
        errors.append(f"Unsupported geometry type '{geometry_type}' for coordinate validation.")

    if raise_error:
        if errors:
            raise ValidationError(errors)
    else:
        return False if errors else True