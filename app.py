from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import math

app = Flask(__name__)

# Storage in memory (not persistent)
entries = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json

    try:
        # User Inputs
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

        else:
            diameter = float(data.get('diameter'))
            depth = float(data.get('depth'))
            radius = diameter / 2
            volume_m3 = math.pi * (radius ** 2) * depth

        volume_litres = volume_m3 * 1000

        # WHO formula
        A = P * q
        target_volume = (2 / 3) * volume_litres
        N = (target_volume - A) / (P * F * S)
        B = P * N * F * S
        check_sum = A + B

        # Next emptying date
        last_date_obj = datetime.strptime(last_emptying_date, "%Y-%m-%d")
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

        # Save this entry
        if lat is not None and lon is not None:
            entries.append({
                "lat": lat,
                "lon": lon,
                "status": status,
                "next_emptying_date": next_emptying_date.strftime("%Y-%m-%d"),
                "N_years": round(N, 2),
                "P": P,
                "created_at": datetime.utcnow().isoformat() + "Z"
            })

        return jsonify({
            "volume_litres": round(volume_litres, 2),
            "target_volume": round(target_volume, 2),
            "A": round(A, 2),
            "B": round(B, 2),
            "check_sum": round(check_sum, 2),
            "N_years": round(N, 2),
            "next_emptying_date": next_emptying_date.strftime("%Y-%m-%d"),
            "status": status
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/entries', methods=['GET'])
def get_entries():
    return jsonify(entries)

if __name__ == '__main__':
    app.run(debug=True)
