from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import math
import csv
import io

app = Flask(__name__)

# In-memory storage for points (reset when service restarts)
entries = []


def parse_last_date(value: str) -> datetime:
    """
    Parse last emptying date from various formats.
    - '2019'              -> 2019-01-01
    - '2019-03-14'
    - '14/03/2019'
    - '14-03-2019'
    - '2019/03/14'
    Raises ValueError if it cannot parse.
    """
    s = (value or "").strip()
    if not s:
        raise ValueError("last_date is empty")

    # Case: only year given
    if len(s) == 4 and s.isdigit():
        year = int(s)
        return datetime(year, 1, 1)

    # Try several common formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    raise ValueError(f"last_date '{s}' not in recognised format")


def compute_and_store_entry(data, name=None):
    """
    Shared logic for single-entry calculation.
    data: dict with last_date, shape, P, q, F, S, dimensions, lat, lon
    Returns a dict with calculation results.
    Also appends to entries[] if lat/lon present.
    """
    last_emptying_date = data.get('last_date')
    shape = data.get('shape')
    P = float(data.get('P'))
    q = float(data.get('q'))
    F = float(data.get('F'))
    S = float(data.get('S'))

    # Lat/Long
    lat_raw = data.get('lat')
    lon_raw = data.get('lon')
    lat = float(lat_raw) if lat_raw not in (None, "",) else None
    lon = float(lon_raw) if lon_raw not in (None, "",) else None

    # Shape Calculations
    if shape == "rectangular":
        length = float(data.get('length'))
        width = float(data.get('width'))
        depth = float(data.get('depth'))
        volume_m3 = length * width * depth
    elif shape == "circular":
        diameter = float(data.get('diameter'))
        depth = float(data.get('depth'))
        radius = diameter / 2
        volume_m3 = math.pi * (radius ** 2) * depth
    else:
        raise ValueError("shape must be 'rectangular' or 'circular'")

    volume_litres = volume_m3 * 1000

    # WHO formula
    A = P * q
    target_volume = (2 / 3) * volume_litres
    N = (target_volume - A) / (P * F * S)
    B = P * N * F * S
    check_sum = A + B

    # Next emptying date (robust date parsing)
    last_date_obj = parse_last_date(last_emptying_date)
    next_emptying_date = last_date_obj + timedelta(days=N * 365)

    # Status category
    today = datetime.today().date()
    next_date_only = next_emptying_date.date()

    if next_date_only < today:
        status = "unhealthy"
    elif next_date_only <= today + timedelta(days=180):
        status = "warning"
    else:
        status = "healthy"

    # Save this entry for map
    if lat is not None and lon is not None:
        entries.append({
            "name": name,
            "lat": lat,
            "lon": lon,
            "status": status,
            "next_emptying_date": next_emptying_date.strftime("%Y-%m-%d"),
            "N_years": round(N, 2),
            "P": P,
            "created_at": datetime.utcnow().isoformat() + "Z"
        })

    return {
        "volume_litres": round(volume_litres, 2),
        "target_volume": round(target_volume, 2),
        "A": round(A, 2),
        "B": round(B, 2),
        "check_sum": round(check_sum, 2),
        "N_years": round(N, 2),
        "next_emptying_date": next_emptying_date.strftime("%Y-%m-%d"),
        "status": status
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    try:
        name = data.get('name')  # optional
        result = compute_and_store_entry(data, name=name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/entries', methods=['GET'])
def get_entries():
    return jsonify(entries)


@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    """
    Accepts a CSV file with header:
    name,last_date,shape,P,q,F,S,length,width,depth,diameter,lat,lon

    last_date can be:
    - full date (e.g. 2019-03-14, 14/03/2019)
    - or just year (e.g. 2019, treated as 2019-01-01)
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    try:
        text = file.stream.read().decode('utf-8', errors='ignore')
        stream = io.StringIO(text)
        reader = csv.DictReader(stream)

        processed = 0
        failed_rows = []

        for i, row in enumerate(reader, start=2):  # line numbers (header is 1)
            try:
                shape = (row.get('shape') or "").strip().lower()

                data = {
                    "last_date": (row.get('last_date') or "").strip(),
                    "shape": shape,
                    "P": row.get('P'),
                    "q": row.get('q'),
                    "F": row.get('F'),
                    "S": row.get('S'),
                    "lat": row.get('lat'),
                    "lon": row.get('lon')
                }

                if shape == "rectangular":
                    data["length"] = row.get('length')
                    data["width"] = row.get('width')
                    data["depth"] = row.get('depth')
                elif shape == "circular":
                    data["diameter"] = row.get('diameter')
                    data["depth"] = row.get('depth')
                else:
                    raise ValueError("shape must be 'rectangular' or 'circular'")

                name = row.get('name')
                compute_and_store_entry(data, name=name)
                processed += 1

            except Exception as e:
                failed_rows.append({"line": i, "error": str(e)})

        return jsonify({
            "processed": processed,
            "failed": failed_rows
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)
