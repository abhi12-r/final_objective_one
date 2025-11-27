        # Lat/Long
        lat_raw = data.get('lat')
        lon_raw = data.get('lon')
        lat = float(lat_raw) if lat_raw not in (None, "",) else None
        lon = float(lon_raw) if lon_raw not in (None, "",) else None

        ...
        # (keep your volume, A, B, N, next_emptying_date logic)

        # ---------- HEALTH CATEGORY ----------
        today = datetime.today().date()
        next_date_only = next_emptying_date.date()

        if next_date_only < today:
            status = "unhealthy"
        elif next_date_only <= today + timedelta(days=180):
            status = "warning"
        else:
            status = "healthy"

        # ---------- STORE ENTRY FOR MAP ----------
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
